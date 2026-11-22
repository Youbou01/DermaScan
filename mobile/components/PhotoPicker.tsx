import { useState } from 'react';
import { Image, Platform, View } from 'react-native';
import { Button, FieldError } from 'heroui-native';
import { AppText } from './AppText';
import { choosePhoto, type LabelPhoto } from '@/lib/photos';
import { errorMessage } from '@/lib/api/client';
import { notifyError } from '@/lib/api/queries';
import { colors } from '@/lib/theme';
export function PhotoPicker({
  value,
  onChange,
  disabled = false,
}: {
  value: LabelPhoto | null;
  onChange: (photo: LabelPhoto | null) => void;
  disabled?: boolean;
}) {
  const [error, setError] = useState('');
  const [pending, setPending] = useState(false);
  async function select(camera: boolean) {
    setError('');
    setPending(true);
    try {
      const photo = await choosePhoto(camera);
      if (photo) onChange(photo);
    } catch (reason) {
      setError(errorMessage(reason));
      notifyError();
    } finally {
      setPending(false);
    }
  }
  return (
    <View style={{ gap: 12 }}>
      {value && (
        <Image
          source={{ uri: value.uri }}
          accessibilityLabel="Selected product label"
          resizeMode="contain"
          style={{
            height: 180,
            width: '100%',
            resizeMode: 'contain',
            backgroundColor: colors.peach,
            borderRadius: 18,
          }}
        />
      )}
      <View style={{ flexDirection: 'row', gap: 10 }}>
        <Button
          variant="secondary"
          style={{ flex: 1 }}
          isDisabled={disabled || pending}
          onPress={() => {
            void select(false);
          }}
        >
          <Button.Label>
            {pending ? 'Opening…' : value ? 'Change photo' : 'Choose photo'}
          </Button.Label>
        </Button>
        {Platform.OS !== 'web' && (
          <Button
            variant="secondary"
            style={{ flex: 1 }}
            isDisabled={disabled || pending}
            onPress={() => {
              void select(true);
            }}
          >
            <Button.Label>Take photo</Button.Label>
          </Button>
        )}
      </View>
      {!!error && <FieldError>{error}</FieldError>}
      <AppText style={{ fontSize: 11, color: colors.muted }}>
        JPEG, PNG or WebP, up to 10 MB.
      </AppText>
    </View>
  );
}
