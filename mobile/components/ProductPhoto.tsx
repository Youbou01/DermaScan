import { useState } from 'react';
import { Image, View } from 'react-native';
import { ImageOff } from 'lucide-react-native';
import { AppText } from './AppText';
import { colors } from '@/lib/theme';
export function publicImageUrl(value: string | null): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    if (
      url.protocol !== 'https:' ||
      url.hostname === 'localhost' ||
      url.hostname === '127.0.0.1' ||
      url.hostname === '0.0.0.0'
    )
      return null;
    return value;
  } catch {
    return null;
  }
}
export function ProductPhoto({
  url,
  name,
  height = 168,
}: {
  url: string | null;
  name: string;
  height?: number;
}) {
  const [failedUrl, setFailedUrl] = useState<string | null>(null);
  const source = publicImageUrl(url);
  return (
    <View
      style={{
        height,
        backgroundColor: colors.peach,
        borderRadius: 18,
        overflow: 'hidden',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 10,
      }}
    >
      {source && source !== failedUrl ? (
        <Image
          source={{ uri: source }}
          accessibilityLabel={name}
          resizeMode="contain"
          style={{ width: '100%', height, resizeMode: 'contain' }}
          onError={() => setFailedUrl(source)}
        />
      ) : (
        <>
          <ImageOff size={32} color={colors.ink} strokeWidth={1.8} />
          <AppText style={{ color: colors.ink, fontSize: 11 }}>Photo unavailable</AppText>
        </>
      )}
    </View>
  );
}
