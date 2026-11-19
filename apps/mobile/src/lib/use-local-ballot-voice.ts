import { useEffect, useRef, useState } from 'react';
import { Alert } from 'react-native';
import * as Speech from 'expo-speech';
import { ExpoSpeechRecognitionModule, useSpeechRecognitionEvent } from 'expo-speech-recognition';

export function useLocalBallotVoice(onCommand: (text: string) => void, enabled: boolean) {
  const [listening, setListening] = useState(false);
  const handler = useRef(onCommand);
  handler.current = onCommand;
  useSpeechRecognitionEvent('start', () => setListening(true));
  useSpeechRecognitionEvent('end', () => setListening(false));
  useSpeechRecognitionEvent('result', event => {
    if (enabled && event.isFinal && event.results[0]?.transcript) handler.current(event.results[0].transcript);
  });
  useSpeechRecognitionEvent('error', event => {
    setListening(false);
    if (event.error !== 'aborted') Alert.alert('Reconocimiento local', 'No se pudo reconocer el comando. Verifique que español esté descargado para uso sin conexión. Puede continuar con los botones.');
  });
  useEffect(() => {
    if (!enabled) { ExpoSpeechRecognitionModule.abort(); void Speech.stop(); }
    return () => { ExpoSpeechRecognitionModule.abort(); void Speech.stop(); };
  }, [enabled]);
  const start = async () => {
    try {
      if (listening) { ExpoSpeechRecognitionModule.stop(); return; }
      if (!ExpoSpeechRecognitionModule.supportsOnDeviceRecognition()) {
        throw new Error('Este dispositivo no dispone de reconocimiento sin conexión. Continúe con los botones.');
      }
      const permission = await ExpoSpeechRecognitionModule.requestPermissionsAsync();
      if (!permission.granted) throw new Error('Debe autorizar el micrófono para usar comandos de voz.');
      await Speech.stop();
      ExpoSpeechRecognitionModule.start({
        lang: 'es-ES', interimResults: false, continuous: false,
        requiresOnDeviceRecognition: true,
        recordingOptions: { persist: false },
      });
    } catch (error) { Alert.alert('Comandos de voz', error instanceof Error ? error.message : 'No se pudo iniciar el micrófono.'); }
  };
  const speak = async (text: string) => {
    await Speech.stop();
    const voices = await Speech.getAvailableVoicesAsync();
    const voice = voices.find(v => v.language.startsWith('es') && !/network|online/i.test(v.identifier));
    if (voice) Speech.speak(text, { voice: voice.identifier, language: voice.language, rate: 0.95 });
  };
  return { listening, start, speak };
}
