import type { ConfigContext, ExpoConfig } from '@expo/config';

type ExpoPlugins = NonNullable<ExpoConfig['plugins']>;

export default ({ config }: ConfigContext): ExpoConfig => {
  const nativePlugins: ExpoPlugins =
    process.env.EXPO_PLATFORM === 'native'
      ? [['expo-dev-client', { launchMode: 'most-recent' }]]
      : [];

  return {
    ...config,
    name: 'DermaScan',
    slug: 'dermascan',
    version: process.env.BILT_APP_VERSION ?? '1.0.0',
    orientation: 'portrait',
    userInterfaceStyle: 'automatic',
    scheme: 'dermascan',
    runtimeVersion: {
      policy: 'appVersion',
    },
    assetBundlePatterns: ['**/*'],
    ios: {
      deploymentTarget: '16.4',
      infoPlist: {
        ITSAppUsesNonExemptEncryption: false,
      },
      supportsTablet: true,
      bundleIdentifier: process.env.BILT_IOS_BUNDLE_ID ?? 'me.bilt.dermascan',
    },
    android: {
      package: process.env.BILT_ANDROID_PACKAGE ?? 'me.bilt.dermascan',
    },
    web: {
      bundler: 'metro',
      // 'single' = SPA export: one index.html + client routing, so edge serving
      // needs only a single 404→index.html fallback rule.
      output: 'single',
      favicon: './public/icons/icon-192.png',
    },
    extra: {
      appStoreAppId: process.env.BILT_APP_STORE_APP_ID,
    },
    plugins: [
      'expo-router',
      'expo-font',
      'expo-splash-screen',
      'expo-secure-store',
      [
        'expo-image-picker',
        {
          photosPermission: 'Allow DermaScan to read a photo of a product label.',
          cameraPermission: 'Allow DermaScan to photograph ingredient labels.',
          microphonePermission: false,
        },
      ],
      [
        'expo-camera',
        {
          cameraPermission: 'Allow DermaScan to scan product barcodes.',
          barcodeScannerEnabled: true,
          recordAudioAndroid: false,
        },
      ],
      ...nativePlugins,
    ],
    experiments: {
      typedRoutes: true,
      reactCompiler: true,
    },
  };
};
