import Constants, { ExecutionEnvironment } from 'expo-constants';
import { AssetRegistry } from 'react-native';

/**
 * Make bundled assets (images, fonts) load in Expo Go behind the Bilt preview proxy.
 *
 * The proxy deletes `extra.expoGo.developer` from the manifest, because Expo Go on a
 * physical iPhone refuses a dev-server manifest that keeps it. expo-asset reads that
 * same field to decide whether to build dev-server asset URLs; without it every
 * `require()`d asset resolves to the published-update CDN instead, where a dev asset
 * was never uploaded, and loads forever.
 *
 * Rewriting each asset's `httpServerLocation` to an absolute URL takes priority over
 * that branch (see expo-asset's `selectAssetSource`). The origin comes from the bundle
 * URL rather than `debuggerHost` so it keeps the proxy's `/<share-token>/` path prefix,
 * which a host-only value would drop.
 */
export function patchExpoGoAssetUrls(): void {
  if (!__DEV__ || Constants.executionEnvironment !== ExecutionEnvironment.StoreClient) return;

  // oxlint-disable-next-line eslint/no-underscore-dangle -- expo-constants names it that
  const base = devServerBase(Constants.__unsafeNoWarnManifest2?.launchAsset?.url);
  if (!base) return;

  const getAssetByID = AssetRegistry.getAssetByID.bind(AssetRegistry);

  AssetRegistry.getAssetByID = (assetId) => {
    const asset = getAssetByID(assetId);
    // Registry entries are shared, so absolutising in place runs once per asset.
    if (asset?.httpServerLocation.startsWith('/')) {
      (asset as { httpServerLocation: string }).httpServerLocation =
        base + asset.httpServerLocation;
    }
    return asset;
  };
}

// Same grammar the preview proxy uses for its path prefix (see metro.config.cjs).
const PREVIEW_TOKEN_PREFIX =
  /^\/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(?=\/|$)/i;

/**
 * Asset root for a bundle URL: origin plus the proxy's token prefix, if any.
 *
 * The rest of the path belongs to the bundle, not to the assets — an expo-router
 * entry is served from `/node_modules/expo-router/entry.bundle`, so anything
 * derived from its directory points nowhere.
 */
export function devServerBase(bundleUrl: string | undefined): string | null {
  const parts = /^(https?:\/\/[^/?#]+)([^?#]*)/.exec(bundleUrl ?? '');
  if (!parts) return null;
  const [, origin, path] = parts;
  return origin + (PREVIEW_TOKEN_PREFIX.exec(path)?.[0] ?? '');
}
