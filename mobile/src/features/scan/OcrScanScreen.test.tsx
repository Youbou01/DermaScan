import React, { type ReactElement } from 'react';
import type { View as RNViewType } from 'react-native';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, waitFor } from '@testing-library/react-native';
import i18n from '@/i18n/i18n';
import { LanguageProvider } from '@/i18n/LanguageProvider';
import { OcrScanScreen } from './OcrScanScreen';

const mockPush = jest.fn();

jest.mock('expo-router', () => ({
  useRouter: () => ({ push: mockPush }),
}));

jest.mock('expo-camera', () => {
  const ReactActual = jest.requireActual<typeof React>('react');
  const { View: RNView } = jest.requireActual<{ View: typeof RNViewType }>('react-native');
  return {
    CameraView: ReactActual.forwardRef(
      (
        props: Record<string, unknown>,
        ref: React.ForwardedRef<{ takePictureAsync: () => Promise<{ uri: string }> }>,
      ) => {
        ReactActual.useImperativeHandle(ref, () => ({
          takePictureAsync: jest.fn().mockResolvedValue({ uri: 'file://mock-photo.jpg' }),
        }));
        return <RNView testID="camera-view" {...props} />;
      },
    ),
    useCameraPermissions: () => [{ granted: true, canAskAgain: true }, jest.fn()],
  };
});

function renderOcrScreen(): ReactElement {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false, gcTime: 0 },
    },
  });
  return (
    <QueryClientProvider client={queryClient}>
      <LanguageProvider>
        <OcrScanScreen />
      </LanguageProvider>
    </QueryClientProvider>
  );
}

describe('OcrScanScreen', () => {
  beforeEach(() => {
    mockPush.mockClear();
  });

  it('shows a validation alert when tapping analyze with empty text', async () => {
    const screen = await render(renderOcrScreen());
    const analyzeButton = screen.getByRole('button', {
      name: i18n.t('ocr.analyze_button'),
    });

    await fireEvent.press(analyzeButton);

    expect(screen.getByRole('alert')).toBeTruthy();
    expect(screen.getByText(i18n.t('ocr.empty_text_error'))).toBeTruthy();
  });

  it('analyzes pasted multilingual ingredients and renders ocr-result-sheet', async () => {
    const screen = await render(renderOcrScreen());
    const input = screen.getByLabelText(i18n.t('ocr.text_label'));

    await fireEvent.changeText(input, 'Aqua, Glycérine, Retinol, Parfum');

    const analyzeButton = screen.getByRole('button', {
      name: i18n.t('ocr.analyze_button'),
    });
    await fireEvent.press(analyzeButton);

    await waitFor(() => {
      expect(screen.getByTestId('ocr-result-sheet')).toBeTruthy();
    });

    expect(screen.getByText(i18n.t('ocr.result_heading'))).toBeTruthy();
    expect(screen.getByText(/1\. Aqua/i)).toBeTruthy();
    expect(screen.getByText(/2\. Glycérine/i)).toBeTruthy();
    expect(screen.getByText(/3\. Retinol/i)).toBeTruthy();
    expect(screen.getByText(/4\. Parfum/i)).toBeTruthy();
  });

  it('captures label photo and triggers instant OCR analysis', async () => {
    const screen = await render(renderOcrScreen());
    const captureButton = screen.getAllByRole('button', {
      name: i18n.t('ocr.capture_photo'),
    })[0]!;

    await fireEvent.press(captureButton);

    await waitFor(() => {
      expect(screen.getByTestId('ocr-result-sheet')).toBeTruthy();
    });

    expect(screen.getByText(i18n.t('ocr.result_heading'))).toBeTruthy();
  });

  it('navigates back to barcode scan screen when tapping switch button', async () => {
    const screen = await render(renderOcrScreen());
    const switchButton = screen.getByRole('button', {
      name: i18n.t('ocr.switch_to_barcode'),
    });

    await fireEvent.press(switchButton);

    expect(mockPush).toHaveBeenCalledWith('/scan');
  });
});
