import { useState } from 'react';
import { Button, Input, Label, FieldError } from 'heroui-native';
import { useMutation } from '@tanstack/react-query';
import { router, useLocalSearchParams } from 'expo-router';
import { Screen } from '@/components/Screen';
import { AppText } from '@/components/AppText';
import { PhotoPicker } from '@/components/PhotoPicker';
import { notifySuccess } from '@/lib/api/queries';
import { request, errorMessage } from '@/lib/api/client';
import { photoForm, type LabelPhoto } from '@/lib/photos';
import type { Contribution } from '@/lib/api/types';
import { colors } from '@/lib/theme';
export default function ContributeScreen() {
  const params = useLocalSearchParams<{ barcode?: string }>();
  const [barcode, setBarcode] = useState(params.barcode ?? '');
  const [photo, setPhoto] = useState<LabelPhoto | null>(null);
  const mutation = useMutation({
    mutationFn: async () => {
      const code = barcode.replace(/[\s-]/g, '');
      if (!/^\d{8}$|^\d{12}$|^\d{13}$/.test(code))
        throw new Error('Enter an 8, 12 or 13-digit product barcode.');
      if (!photo) throw new Error('Choose a clear photo of the product’s ingredient label.');
      const form = await photoForm(photo);
      form.append('barcode', code);
      return request<Contribution>('/contributions', { method: 'POST', body: form });
    },
    onSuccess: notifySuccess,
  });
  return (
    <Screen title="Submit a product">
      {mutation.data ? (
        <>
          <AppText weight="semibold" style={{ fontSize: 28 }}>
            {mutation.data.status === 'quarantined'
              ? 'Submitted for review.'
              : 'Product submitted.'}
          </AppText>
          <AppText style={{ lineHeight: 22, color: colors.muted }}>
            Your submission has been received. It may take time to appear in the catalog.
          </AppText>
          <Button onPress={() => router.replace('/')}>
            <Button.Label>Explore products</Button.Label>
          </Button>
          <Button
            variant="tertiary"
            onPress={() => {
              mutation.reset();
              setBarcode('');
              setPhoto(null);
            }}
          >
            <Button.Label>Submit another product</Button.Label>
          </Button>
        </>
      ) : (
        <>
          <AppText weight="semibold" style={{ fontSize: 28 }}>
            Help fill the shelf.
          </AppText>
          <Label>Barcode</Label>
          <Input
            value={barcode}
            onChangeText={setBarcode}
            keyboardType="number-pad"
            editable={!mutation.isPending}
            accessibilityLabel="Product barcode"
          />
          <Label>Ingredient label photo</Label>
          <PhotoPicker value={photo} onChange={setPhoto} disabled={mutation.isPending} />
          {mutation.isError && <FieldError>{errorMessage(mutation.error)}</FieldError>}
          <Button isDisabled={mutation.isPending} onPress={() => mutation.mutate()}>
            <Button.Label>{mutation.isPending ? 'Submitting…' : 'Submit product'}</Button.Label>
          </Button>
        </>
      )}
    </Screen>
  );
}
