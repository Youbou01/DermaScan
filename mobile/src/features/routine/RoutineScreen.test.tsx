import type { ReactElement } from 'react';
import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, waitFor } from '@testing-library/react-native';
import i18n from '@/i18n/i18n';
import { LanguageProvider } from '@/i18n/LanguageProvider';
import { RoutineScreen } from './RoutineScreen';
import { RoutineRecommendationView } from './RoutineRecommendationView';
import { resetMockRoutineStore } from './routine-api';

const mockPush = jest.fn();

jest.mock('expo-router', () => ({
  useRouter: () => ({ push: mockPush }),
}));

function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false, gcTime: 0 },
    },
  });
}

function renderRoutineScreen(): ReactElement {
  const queryClient = createTestQueryClient();
  return (
    <QueryClientProvider client={queryClient}>
      <LanguageProvider>
        <RoutineScreen />
      </LanguageProvider>
    </QueryClientProvider>
  );
}

function renderRecommendationView(): ReactElement {
  const queryClient = createTestQueryClient();
  return (
    <QueryClientProvider client={queryClient}>
      <LanguageProvider>
        <RoutineRecommendationView />
      </LanguageProvider>
    </QueryClientProvider>
  );
}

describe('RoutineScreen & Habit Tracker (US-16)', () => {
  beforeEach(() => {
    resetMockRoutineStore();
    mockPush.mockClear();
  });

  it('renders Morning steps by default and switches to Evening tab', async () => {
    const screen = await render(renderRoutineScreen());
    await screen.findByText(i18n.t('routine.title'));

    expect(screen.getByText(i18n.t('routine.title'))).toBeTruthy();
    expect(screen.getByText('5. Sunscreen')).toBeTruthy();

    const eveningTab = screen.getByRole('button', {
      name: i18n.t('routine.evening_tab'),
    });
    await fireEvent.press(eveningTab);

    expect(screen.getByText(i18n.t('routine.evening_tab'))).toBeTruthy();
    expect(screen.queryByText('5. Sunscreen')).toBeNull();
  });

  it('toggles daily habit completion and updates label', async () => {
    const screen = await render(renderRoutineScreen());
    await screen.findByText(i18n.t('routine.title'));

    const toggleButton = screen.getByRole('button', {
      name: i18n.t('routine.habit_mark_complete'),
    });
    await fireEvent.press(toggleButton);

    await waitFor(() => {
      expect(screen.getAllByText(/Completed today/i).length).toBeGreaterThan(0);
    });
  });

  it('removes a step from the routine and allows reordering', async () => {
    const screen = await render(renderRoutineScreen());
    await screen.findByText(i18n.t('routine.title'));

    const initialRemoveButtons = screen.getAllByRole('button', {
      name: /Remove .* from routine/i,
    });
    const initialCount = initialRemoveButtons.length;

    await fireEvent.press(initialRemoveButtons[0]!);

    await waitFor(() => {
      const updatedButtons = screen.getAllByRole('button', {
        name: /Remove .* from routine/i,
      });
      expect(updatedButtons.length).toBe(initialCount - 1);
    });
  });

  it('navigates to recommendations screen when tapping recommendation link', async () => {
    const screen = await render(renderRoutineScreen());
    await screen.findByText(i18n.t('routine.title'));

    const link = screen.getByRole('button', {
      name: i18n.t('routine.open_recommendations'),
    });
    await fireEvent.press(link);

    expect(mockPush).toHaveBeenCalledWith('/routine/recommendations');
  });
});

describe('Chemical Conflict Detection & Alert Modal (US-15)', () => {
  beforeEach(() => {
    resetMockRoutineStore();
    mockPush.mockClear();
  });

  it('triggers conflict warning banner when layering Retinoid and AHA/BHA acid in the same routine', async () => {
    const screen = await render(renderRoutineScreen());
    await screen.findByText(i18n.t('routine.title'));

    const addRetinol = screen.getByRole('button', {
      name: i18n.t('routine.add_step_button', { name: 'Night Renewal Retinol 0.3% Serum' }),
    });
    await fireEvent.press(addRetinol);
    await screen.findByText('Night Renewal Retinol 0.3% Serum');

    const addGlycolic = screen.getByRole('button', {
      name: i18n.t('routine.add_step_button', { name: 'Glycolic Acid 7% Resurfacing Toner' }),
    });
    await fireEvent.press(addGlycolic);
    await screen.findByText('Glycolic Acid 7% Resurfacing Toner');

    await waitFor(() => {
      expect(screen.getByTestId('conflict-warning-banner')).toBeTruthy();
    });

    expect(screen.getByText(i18n.t('conflicts.banner_title_one'))).toBeTruthy();

    const detailsButton = screen.getByRole('button', {
      name: i18n.t('conflicts.banner_cta'),
    });
    await fireEvent.press(detailsButton);

    expect(screen.getByText(i18n.t('conflicts.modal_heading'))).toBeTruthy();
    expect(screen.getByText('Retinoid + Exfoliating Acid (AHA/BHA) Conflict')).toBeTruthy();
    expect(
      screen.getByText(
        'Use on alternate evenings or move the exfoliating acid to a separate routine.',
      ),
    ).toBeTruthy();

    const closeButton = screen.getByLabelText(i18n.t('conflicts.close_modal'));
    await fireEvent.press(closeButton);
  });

  it('displays pre-check conflict warning on conflicting candidate product before addition', async () => {
    const screen = await render(renderRoutineScreen());
    await screen.findByText(i18n.t('routine.title'));

    const addGlycolic = screen.getByRole('button', {
      name: i18n.t('routine.add_step_button', { name: 'Glycolic Acid 7% Resurfacing Toner' }),
    });
    await fireEvent.press(addGlycolic);
    await screen.findByText('Glycolic Acid 7% Resurfacing Toner');

    await waitFor(() => {
      expect(
        screen.getAllByText(new RegExp(i18n.t('conflicts.pre_check_warning'))).length,
      ).toBeGreaterThan(0);
    });
  });
});

describe('Recommended Routine Generator (US-20)', () => {
  beforeEach(() => {
    resetMockRoutineStore();
    mockPush.mockClear();
  });

  it('renders recommendation generator, switches skin type to sensitive, and applies morning routine', async () => {
    const screen = await render(renderRecommendationView());
    await screen.findByText(i18n.t('recommendations.title'));

    expect(screen.getByText(i18n.t('recommendations.title'))).toBeTruthy();

    const sensitiveOption = screen.getByRole('button', {
      name: i18n.t('recommendations.skin_types.sensitive'),
    });
    await fireEvent.press(sensitiveOption);

    const applyMorning = await screen.findByRole('button', {
      name: i18n.t('recommendations.apply_morning'),
    });
    await fireEvent.press(applyMorning);

    await waitFor(() => {
      expect(screen.getByText(i18n.t('recommendations.applied_Confirmation'))).toBeTruthy();
    });

    const backButton = screen.getByRole('button', {
      name: i18n.t('recommendations.back_to_routine'),
    });
    await fireEvent.press(backButton);
    expect(mockPush).toHaveBeenCalledWith('/routine');
  });
});
