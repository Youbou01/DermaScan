import { useRef, useState } from 'react';
import { View } from 'react-native';
import { Button, Input, Label, FieldError, Spinner } from 'heroui-native';
import { router } from 'expo-router';
import BarcodeCamera from '@/components/BarcodeCamera';
import { AppText } from '@/components/AppText';
import { Screen } from '@/components/Screen';
import { ApiError, errorMessage, request } from '@/lib/api/client';
import { notifyError, notifySuccess, queryClient } from '@/lib/api/queries';
import type { ProductDetail } from '@/lib/api/types';
export default function ScanScreen() {
  const [barcode, setBarcode] = useState('');
  const [message, setMessage] = useState('');
  const [active, setActive] = useState(true);
  const [pending, setPending] = useState(false);
  const [missing, setMissing] = useState(false);
  const lock = useRef(false);
  async function lookup(code: string) {
    if (lock.current) return;
    lock.current = true;
    setActive(false);
    setMessage('');
    setMissing(false);
    const normalized = code.replace(/[\s-]/g, '');
    setBarcode(normalized);
    if (!/^\d{8}$|^\d{12}$|^\d{13}$/.test(normalized)) {
      setMessage('Enter an 8, 12 or 13-digit product barcode.');
      notifyError();
      lock.current = false;
      return;
    }
    setPending(true);
    try {
      const product = await request<ProductDetail>(
        '/products/by-barcode/' + encodeURIComponent(normalized),
      );
      queryClient.setQueryData(['product', product.id], product);
      notifySuccess();
      router.replace({ pathname: '/product/[id]', params: { id: product.id } });
    } catch (error) {
      const notFound = error instanceof ApiError && error.status === 404;
      setMissing(notFound);
      setMessage(notFound ? 'This product is not in the catalog yet.' : errorMessage(error));
      notifyError();
    } finally {
      setPending(false);
      lock.current = false;
    }
  }
  return (
    <Screen title="Scan a product">
      <AppText weight="semibold" style={{ fontSize: 28 }}>
        What&apos;s in your bottle?
      </AppText>
      <BarcodeCamera
        active={active && !pending}
        onScan={(code) => {
          void lookup(code);
        }}
      />
      {pending && <Spinner />}
      {!!message && (
        <View style={{ gap: 12 }}>
          <FieldError>{message}</FieldError>
          <Button
            variant="secondary"
            onPress={() => {
              setActive(true);
              setMessage('');
              setMissing(false);
            }}
          >
            <Button.Label>Scan again</Button.Label>
          </Button>
          {missing && (
            <Button
              variant="tertiary"
              onPress={() => router.push({ pathname: '/contribute', params: { barcode } })}
            >
              <Button.Label>Submit this product</Button.Label>
            </Button>
          )}
        </View>
      )}
      <View style={{ gap: 12 }}>
        <Label>Barcode</Label>
        <Input
          value={barcode}
          onChangeText={setBarcode}
          placeholder="Enter the product barcode"
          accessibilityLabel="Product barcode"
          keyboardType="number-pad"
          returnKeyType="search"
          onSubmitEditing={() => {
            void lookup(barcode);
          }}
        />
        <Button
          isDisabled={pending}
          onPress={() => {
            void lookup(barcode);
          }}
        >
          <Button.Label>{pending ? 'Finding product…' : 'Find product'}</Button.Label>
        </Button>
      </View>
      <Button variant="tertiary" onPress={() => router.push('/analysis')}>
        <Button.Label>Read an ingredient label instead</Button.Label>
      </Button>
    </Screen>
  );
}
