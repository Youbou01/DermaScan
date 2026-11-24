import { useState } from 'react';
import { View } from 'react-native';
import { Button, FieldError, Label, TextArea } from 'heroui-native';
import { Star } from 'lucide-react-native';
import { router, useLocalSearchParams } from 'expo-router';
import * as Haptics from 'expo-haptics';
import { useMutation } from '@tanstack/react-query';
import { Screen } from '@/components/Screen';
import { AppText } from '@/components/AppText';
import { SignInGate } from '@/components/DataState';
import { notifySuccess, privateKey, queryClient, useUserId } from '@/lib/api/queries';
import { ApiError, errorMessage, request } from '@/lib/api/client';
import type { Review } from '@/lib/api/types';
import { validateReviewInput } from '@/lib/reviews';
import { colors } from '@/lib/theme';

export default function NewReviewScreen() {
  const { productId, productName } = useLocalSearchParams<{
    productId?: string;
    productName?: string;
  }>();
  const uid = useUserId();

  const [rating, setRating] = useState(0);
  const [body, setBody] = useState('');
  const [validationError, setValidationError] = useState('');

  const mutation = useMutation({
    mutationFn: async () => {
      const errorMsg = validateReviewInput(rating, body);
      if (errorMsg) {
        throw new Error(errorMsg);
      }
      return request<Review>(`/products/${encodeURIComponent(productId ?? '')}/reviews`, {
        method: 'POST',
        auth: true,
        body: { rating, body: body.trim() },
      });
    },
    onSuccess: () => {
      notifySuccess();
      if (productId) {
        void queryClient.invalidateQueries({ queryKey: ['product', productId] });
        void queryClient.invalidateQueries({ queryKey: ['product-reviews', productId] });
      }
      void queryClient.invalidateQueries({ queryKey: privateKey('my-reviews', uid) });
      void queryClient.invalidateQueries({ queryKey: ['products'] });
      router.back();
    },
  });

  if (!uid) {
    return (
      <Screen title="Submit your review">
        <SignInGate message="Sign in to post a review." />
      </Screen>
    );
  }

  const handleSubmit = () => {
    const errorMsg = validateReviewInput(rating, body);
    if (errorMsg) {
      setValidationError(errorMsg);
      return;
    }
    setValidationError('');
    mutation.mutate();
  };

  const serverError =
    mutation.isError && mutation.error instanceof ApiError && mutation.error.status === 409
      ? 'You have already reviewed this product.'
      : mutation.isError
        ? errorMessage(mutation.error)
        : null;

  return (
    <Screen title="Submit your review">
      <View style={{ gap: 20 }}>
        {!!productName && (
          <View style={{ gap: 4 }}>
            <AppText style={{ fontSize: 13, color: colors.muted }}>Product</AppText>
            <AppText weight="semibold" style={{ fontSize: 20 }}>
              {productName}
            </AppText>
          </View>
        )}

        <View style={{ gap: 8 }}>
          <Label>Your rating (1 to 5 stars)</Label>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
            {[1, 2, 3, 4, 5].map((starIndex) => (
              <Button
                key={starIndex}
                isIconOnly
                variant="tertiary"
                accessibilityLabel={`Rate ${starIndex} out of 5 stars`}
                onPress={() => {
                  setRating(starIndex);
                  setValidationError('');
                  void Haptics.selectionAsync();
                }}
              >
                <Star
                  size={32}
                  color={starIndex <= rating ? colors.amber : colors.border}
                  fill={starIndex <= rating ? colors.amber : 'transparent'}
                />
              </Button>
            ))}
          </View>
        </View>

        <View style={{ gap: 8 }}>
          <Label>Your experience</Label>
          <TextArea
            accessibilityLabel="Review body"
            placeholder="Write your review here..."
            value={body}
            onChangeText={(text) => {
              setBody(text);
              setValidationError('');
            }}
            maxLength={2000}
            editable={!mutation.isPending}
            style={{ minHeight: 140 }}
          />
          <AppText style={{ fontSize: 12, color: colors.muted, textAlign: 'right' }}>
            {body.length} / 2000
          </AppText>
        </View>

        {validationError ? (
          <FieldError>{validationError}</FieldError>
        ) : serverError ? (
          <FieldError>{serverError}</FieldError>
        ) : null}

        <View style={{ gap: 10, marginTop: 10 }}>
          <Button isDisabled={mutation.isPending} onPress={handleSubmit}>
            <Button.Label>{mutation.isPending ? 'Submitting…' : 'Submit review'}</Button.Label>
          </Button>

          <Button variant="secondary" isDisabled={mutation.isPending} onPress={() => router.back()}>
            <Button.Label>Cancel</Button.Label>
          </Button>
        </View>
      </View>
    </Screen>
  );
}
