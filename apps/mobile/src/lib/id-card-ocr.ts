import * as ImagePicker from 'expo-image-picker';
import * as FileSystem from 'expo-file-system';
import TextRecognition from '@react-native-ml-kit/text-recognition';

export async function scanIdCard(source: 'camera' | 'library'): Promise<string | null> {
  if (source === 'camera') {
    const permission = await ImagePicker.requestCameraPermissionsAsync();
    if (!permission.granted) throw new Error('Autorice la cámara o seleccione una foto de su galería.');
  }
  const options: ImagePicker.ImagePickerOptions = {
    mediaTypes: ImagePicker.MediaTypeOptions.Images,
    quality: 1,
    base64: false,
    exif: false,
  };
  const result = source === 'camera'
    ? await ImagePicker.launchCameraAsync(options)
    : await ImagePicker.launchImageLibraryAsync(options);
  if (result.canceled || !result.assets[0]) return null;
  const uri = result.assets[0].uri;
  try {
    const recognized = await TextRecognition.recognize(uri);
    if (!recognized.text.trim()) throw new Error('No se detectó texto. Repita la foto con buena luz y sin reflejos.');
    return recognized.text.trim();
  } finally {
    // El selector devuelve una copia temporal; nunca borrar el original de la galería.
    if (FileSystem.cacheDirectory && uri.startsWith(FileSystem.cacheDirectory)) {
      await FileSystem.deleteAsync(uri, { idempotent: true });
    }
  }
}
