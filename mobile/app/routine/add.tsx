import { useEffect, useState } from 'react';
import { FlatList, KeyboardAvoidingView, Platform, View } from 'react-native';
import { Button, Input, Label, FieldError } from 'heroui-native';
import { router, useLocalSearchParams } from 'expo-router';
import { useMutation } from '@tanstack/react-query';
import * as Haptics from 'expo-haptics';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { AppText } from '@/components/AppText';
import { ScreenHeader } from '@/components/Screen';
import { Conflicts } from '@/components/Conflicts';
import { DataState, LoadingState, SignInGate } from '@/components/DataState';
import {
  useProducts,
  useProduct,
  useUserId,
  queryClient,
  privateKey,
  notifySuccess,
} from '@/lib/api/queries';
import { errorMessage, request } from '@/lib/api/client';
import { routineInputs, findRoutine } from '@/lib/routines';
import {
  stepTypes,
  type Conflict,
  type Product,
  type Routine,
  type Slot,
  type StepType,
} from '@/lib/api/types';
import { colors } from '@/lib/theme';
export default function AddRoutineStep() {
  const params = useLocalSearchParams<{ slot?: string; productId?: string }>();
  const uid = useUserId();
  const insets = useSafeAreaInsets();
  const [slot, setSlot] = useState<Slot>(params.slot === 'evening' ? 'evening' : 'morning');
  const [type, setType] = useState<StepType>('serum');
  const [notes, setNotes] = useState('');
  const [query, setQuery] = useState('');
  const [debounced, setDebounced] = useState('');
  const [selected, setSelected] = useState<Product | null>(null);
  const [conflicts, setConflicts] = useState<Conflict[] | null>(null);
  const initial = useProduct(params.productId ?? '');
  const product = selected ?? initial.data ?? null;
  const results = useProducts({ q: debounced }, !!debounced && !!uid);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(query.trim()), 350);
    return () => clearTimeout(timer);
  }, [query]);
  const mutation = useMutation({
    mutationFn: async (confirmed: boolean) => {
      if (!product) throw new Error('Choose a product first.');
      const current = await request<{ routines: Routine[] }>('/routines', { auth: true });
      const steps = findRoutine(current.routines, slot)?.steps ?? [];
      if (steps.some((step) => step.product.id === product.id))
        throw new Error('This product is already in the routine.');
      const check = await request<{ has_conflict: boolean; conflicts: Conflict[] }>(
        `/routines/${slot}/check-conflict/${product.id}`,
        { method: 'POST', auth: true },
      );
      if (check.has_conflict && !confirmed) {
        setConflicts(check.conflicts);
        return false;
      }
      await request<Routine>(`/routines/${slot}`, {
        auth: true,
        method: 'PUT',
        body: {
          steps: [
            ...routineInputs(steps),
            {
              step_order: steps.length + 1,
              step_type: type,
              product_id: product.id,
              notes: notes.trim() || null,
            },
          ],
        },
      });
      return true;
    },
    onSuccess: (saved) => {
      if (saved) {
        notifySuccess();
        void queryClient.invalidateQueries({ queryKey: privateKey('routines', uid) });
        router.dismissTo('/routines');
      }
    },
  });
  const reset = () => {
    setConflicts(null);
    mutation.reset();
    void Haptics.selectionAsync();
  };
  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      style={{ flex: 1, backgroundColor: colors.background }}
    >
      <ScreenHeader title="Add a routine step" />
      <FlatList
        data={uid && !product ? (results.data?.pages.flatMap((page) => page.items) ?? []) : []}
        keyExtractor={(item) => item.id}
        keyboardShouldPersistTaps="handled"
        contentContainerStyle={{ padding: 22, paddingBottom: 20, gap: 12 }}
        onEndReached={() => {
          if (results.hasNextPage && !results.isFetchingNextPage) void results.fetchNextPage();
        }}
        ListHeaderComponent={
          !uid ? (
            <SignInGate />
          ) : (
            <View style={{ gap: 18 }}>
              <AppText weight="semibold" style={{ fontSize: 28 }}>
                Make room for a step.
              </AppText>
              <View style={{ flexDirection: 'row', gap: 10 }}>
                {(['morning', 'evening'] as const).map((value) => (
                  <Button
                    key={value}
                    style={{ flex: 1 }}
                    isDisabled={mutation.isPending}
                    variant={slot === value ? 'primary' : 'secondary'}
                    onPress={() => {
                      setSlot(value);
                      reset();
                    }}
                  >
                    <Button.Label>{value === 'morning' ? 'Morning' : 'Evening'}</Button.Label>
                  </Button>
                ))}
              </View>
              {product ? (
                <View style={{ gap: 10 }}>
                  <AppText weight="semibold">{product.name}</AppText>
                  <Button
                    size="sm"
                    variant="tertiary"
                    isDisabled={mutation.isPending}
                    onPress={() => {
                      setSelected(null);
                      router.setParams({ productId: '' });
                      reset();
                    }}
                  >
                    <Button.Label>Choose another product</Button.Label>
                  </Button>
                </View>
              ) : (
                <>
                  <Label>Find a product</Label>
                  <Input
                    value={query}
                    onChangeText={setQuery}
                    maxLength={100}
                    placeholder="Product name"
                    accessibilityLabel="Find a routine product"
                  />
                  {!!params.productId && initial.isPending && <LoadingState />}
                  {initial.isError && (
                    <DataState
                      error={initial.error}
                      onAction={() => {
                        void initial.refetch();
                      }}
                    />
                  )}
                </>
              )}
              {product && (
                <>
                  <Label>Step type</Label>
                  <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
                    {stepTypes.map((value) => (
                      <Button
                        key={value}
                        size="sm"
                        isDisabled={mutation.isPending}
                        variant={type === value ? 'primary' : 'secondary'}
                        onPress={() => {
                          setType(value);
                          reset();
                        }}
                      >
                        <Button.Label>
                          {value.charAt(0).toUpperCase() + value.slice(1)}
                        </Button.Label>
                      </Button>
                    ))}
                  </View>
                  <Label>Notes</Label>
                  <Input
                    value={notes}
                    onChangeText={setNotes}
                    maxLength={500}
                    editable={!mutation.isPending}
                    accessibilityLabel="Routine step notes"
                  />
                </>
              )}
              {conflicts && (
                <>
                  <AppText weight="semibold" style={{ color: colors.orange }}>
                    Review these conflicts first
                  </AppText>
                  <Conflicts conflicts={conflicts} />
                </>
              )}
              {mutation.isError && <FieldError>{errorMessage(mutation.error)}</FieldError>}
            </View>
          )
        }
        renderItem={({ item }) => (
          <Button
            variant="tertiary"
            style={{ height: 'auto', paddingVertical: 14, justifyContent: 'flex-start' }}
            onPress={() => {
              setSelected(item);
              reset();
            }}
          >
            <Button.Label style={{ textAlign: 'left' }}>{item.name}</Button.Label>
          </Button>
        )}
        ListEmptyComponent={
          uid && !product && debounced ? (
            results.isPending ? (
              <LoadingState />
            ) : results.isError ? (
              <DataState
                error={results.error}
                onAction={() => {
                  void results.refetch();
                }}
              />
            ) : (
              <DataState
                message="No products match."
                action="Clear search"
                onAction={() => setQuery('')}
              />
            )
          ) : undefined
        }
        ListFooterComponent={
          results.isFetchingNextPage ? (
            <LoadingState />
          ) : !product &&
            results.isError &&
            !!results.data?.pages.some((page) => page.items.length > 0) ? (
            <DataState
              error={results.error}
              onAction={() => {
                void results.fetchNextPage();
              }}
            />
          ) : undefined
        }
      />
      {uid && (
        <View
          style={{
            padding: 18,
            paddingBottom: insets.bottom + 18,
            backgroundColor: colors.background,
            borderTopWidth: 1,
            borderTopColor: colors.border,
          }}
        >
          <Button
            isDisabled={!product || mutation.isPending}
            onPress={() => mutation.mutate(!!conflicts)}
          >
            <Button.Label>
              {mutation.isPending
                ? 'Checking and saving…'
                : conflicts
                  ? 'Add despite conflicts'
                  : 'Add step'}
            </Button.Label>
          </Button>
        </View>
      )}
    </KeyboardAvoidingView>
  );
}
