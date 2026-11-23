import { Platform } from 'react-native';
import * as ImagePicker from 'expo-image-picker';
export type LabelPhoto = { uri: string; mimeType: string; fileName: string; fileSize?: number };
export async function choosePhoto(camera = false): Promise<LabelPhoto | null> {
  if (camera) {
    const permission = await ImagePicker.requestCameraPermissionsAsync();
    if (!permission.granted) throw new Error('Allow camera access to photograph a label.');
  }
  const options: ImagePicker.ImagePickerOptions = {
    mediaTypes: ['images'],
    quality: 0.85,
    allowsMultipleSelection: false,
  };
  const result = camera
    ? await ImagePicker.launchCameraAsync(options)
    : await ImagePicker.launchImageLibraryAsync(options);
  if (result.canceled) return null;
  const asset = result.assets[0];
  const mimeType = asset.mimeType ?? 'image/jpeg';
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(mimeType))
    throw new Error('Choose a JPEG, PNG or WebP photo.');
  if (asset.fileSize && asset.fileSize > 10 * 1024 * 1024)
    throw new Error('Choose a photo smaller than 10 MB.');
  return {
    uri: asset.uri,
    mimeType,
    fileName: asset.fileName ?? `label.${mimeType.split('/')[1]}`,
    fileSize: asset.fileSize,
  };
}
export async function photoForm(photo: LabelPhoto) {
  const form = new FormData();
  if (Platform.OS === 'web') {
    const response = await fetch(photo.uri);
    const blob = await response.blob();
    if (blob.size > 10 * 1024 * 1024) throw new Error('Choose a photo smaller than 10 MB.');
    form.append('photo', blob, photo.fileName);
  } else {
    const nativePhoto = {
      uri: photo.uri,
      type: photo.mimeType,
      name: photo.fileName,
    };
    // eslint-disable-next-line typescript/no-unsafe-type-assertion -- React Native FormData accepts URI file descriptors, but the active DOM declarations only accept Blob.
    form.append('photo', nativePhoto as unknown as Blob);
  }
  return form;
}
