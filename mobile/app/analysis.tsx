import { useState } from 'react';
import { View } from 'react-native';
import { Button, Input, Label, TextArea, FieldError } from 'heroui-native';
import { useMutation } from '@tanstack/react-query';
import { router } from 'expo-router';
import * as Haptics from 'expo-haptics';
import { Screen } from '@/components/Screen';
import { AppText } from '@/components/AppText';
import { SignInGate } from '@/components/DataState';
import { PhotoPicker } from '@/components/PhotoPicker';
import { Formula, AnalysisScore } from '@/components/Formula';
import { notifySuccess, useUserId } from '@/lib/api/queries';
import { errorMessage, request } from '@/lib/api/client';
import { photoForm, type LabelPhoto } from '@/lib/photos';
import type { Analysis } from '@/lib/api/types';
import { colors } from '@/lib/theme';
export default function AnalysisScreen() {
  const uid = useUserId();
  const [mode, setMode] = useState<'text' | 'photo'>('text');
  const [text, setText] = useState('');
  const [name, setName] = useState('');
  const [photo, setPhoto] = useState<LabelPhoto | null>(null);
  const mutation = useMutation({
    mutationFn: async () => {
      if (mode === 'text') {
        if (text.trim().length < 3) throw new Error('Enter the ingredient list from the label.');
        return request<Analysis>('/analysis/text', {
          auth: true,
          method: 'POST',
          body: { text: text.trim(), product_name: name.trim() || undefined },
        });
      }
      if (!photo) throw new Error('Choose a clear photo of the ingredient list.');
      const form = await photoForm(photo);
      if (name.trim()) form.append('product_name', name.trim());
      return request<Analysis>('/analysis/ocr', { auth: true, method: 'POST', body: form });
    },
    onSuccess: notifySuccess,
  });
  return (
    <Screen title="Read a label">
      {!uid ? (
        <SignInGate message="Sign in to analyze an ingredient label." />
      ) : (
        <>
          <AppText weight="semibold" style={{ fontSize: 28 }}>
            Look past the packaging.
          </AppText>
          <View style={{ flexDirection: 'row', gap: 10 }}>
            {(['text', 'photo'] as const).map((value) => (
              <Button
                key={value}
                style={{ flex: 1 }}
                variant={mode === value ? 'primary' : 'secondary'}
                isDisabled={mutation.isPending}
                onPress={() => {
                  setMode(value);
                  mutation.reset();
                  void Haptics.selectionAsync();
                }}
              >
                <Button.Label>
                  {value === 'text' ? 'Paste ingredients' : 'Label photo'}
                </Button.Label>
              </Button>
            ))}
          </View>
          <Label>Product name (optional)</Label>
          <Input
            value={name}
            onChangeText={setName}
            maxLength={255}
            editable={!mutation.isPending}
            accessibilityLabel="Product name"
          />
          {mode === 'text' ? (
            <>
              <Label>Ingredient list</Label>
              <TextArea
                value={text}
                onChangeText={setText}
                maxLength={10000}
                editable={!mutation.isPending}
                placeholder="Paste the full ingredient list"
                accessibilityLabel="Ingredient list"
                style={{ minHeight: 160 }}
              />
            </>
          ) : (
            <PhotoPicker
              value={photo}
              onChange={(value) => {
                setPhoto(value);
                mutation.reset();
              }}
              disabled={mutation.isPending}
            />
          )}
          {mutation.isError && <FieldError>{errorMessage(mutation.error)}</FieldError>}
          <Button isDisabled={mutation.isPending} onPress={() => mutation.mutate()}>
            <Button.Label>{mutation.isPending ? 'Analyzing…' : 'Analyze ingredients'}</Button.Label>
          </Button>
          {mutation.data && (
            <>
              <AnalysisScore analysis={mutation.data} />
              {mode === 'photo' && !!mutation.data.extracted_text && (
                <View style={{ gap: 10 }}>
                  <AppText weight="medium">Text read from the photo</AppText>
                  <AppText style={{ lineHeight: 21, color: colors.muted }}>
                    {mutation.data.extracted_text}
                  </AppText>
                  <Button
                    variant="secondary"
                    onPress={() => {
                      setText(mutation.data?.extracted_text ?? '');
                      setMode('text');
                      mutation.reset();
                      void Haptics.selectionAsync();
                    }}
                  >
                    <Button.Label>Correct and analyze text</Button.Label>
                  </Button>
                </View>
              )}
              <Formula
                analysis={mutation.data}
                onEmpty={() => {
                  mutation.reset();
                  setMode('text');
                }}
              />
              <AppText style={{ fontSize: 12, color: colors.muted }}>
                This label analysis is not saved to the product catalog.
              </AppText>
              <Button variant="tertiary" onPress={() => router.push('/contribute')}>
                <Button.Label>Submit a product</Button.Label>
              </Button>
            </>
          )}
        </>
      )}
    </Screen>
  );
}
