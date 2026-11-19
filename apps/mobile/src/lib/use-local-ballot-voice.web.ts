import { Alert } from 'react-native';
export function useLocalBallotVoice(_command: (text: string) => void, _enabled: boolean) {
  return { listening: false, start: async () => { Alert.alert('Voz', 'Use el portal web o la app Android/iOS.'); }, speak: async (_text: string) => {} };
}
