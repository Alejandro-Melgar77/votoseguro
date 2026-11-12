import React, { useState, useEffect } from 'react';
import { StyleSheet, View, Linking, SafeAreaView } from 'react-native';
import { StatusBar } from 'expo-status-bar';

import { HomePortalScreen } from './src/screens/HomePortalScreen';
import { VoterRegistrationScreen } from './src/screens/VoterRegistrationScreen';
import { MobileBallotBoothScreen } from './src/screens/MobileBallotBoothScreen';
import { MobileReceiptVerifierScreen } from './src/screens/MobileReceiptVerifierScreen';
import { MobileFaqAssistantScreen } from './src/screens/MobileFaqAssistantScreen';

type ScreenType = 'home' | 'register' | 'booth' | 'receipt' | 'faq';

interface NavigationParams {
  token?: string;
  receiptHash?: string;
  electionId?: string;
}

export default function App() {
  const [currentScreen, setCurrentScreen] = useState<ScreenType>('home');
  const [screenParams, setScreenParams] = useState<NavigationParams>({});

  // Manejador de navegación universal
  const handleNavigate = (screen: ScreenType, params?: NavigationParams) => {
    if (params) {
      setScreenParams(params);
    } else {
      setScreenParams({});
    }
    setCurrentScreen(screen);
  };

  // Procesamiento de Deep Links (S2-01)
  const handleDeepLink = (url: string | null) => {
    if (!url) return;

    try {
      // Soporta votoseguro://register/:token y votoseguro://receipt/:hash
      const parsedUrl = new URL(url);
      const hostOrPath = parsedUrl.hostname || parsedUrl.pathname.replace(/^\/\//, '');

      if (hostOrPath.startsWith('register')) {
        const parts = parsedUrl.pathname.split('/').filter(Boolean);
        const tokenFromPath = parts[0] === 'register' ? parts[1] : parts[0];
        const token = tokenFromPath || parsedUrl.searchParams.get('token') || '';
        handleNavigate('register', { token });
      } else if (hostOrPath.startsWith('receipt')) {
        const parts = parsedUrl.pathname.split('/').filter(Boolean);
        const hashFromPath = parts[0] === 'receipt' ? parts[1] : parts[0];
        const receiptHash = hashFromPath || parsedUrl.searchParams.get('hash') || '';
        handleNavigate('receipt', { receiptHash });
      } else if (hostOrPath.startsWith('booth')) {
        handleNavigate('booth');
      } else if (hostOrPath.startsWith('faq')) {
        handleNavigate('faq');
      }
    } catch {
      // Si la URL no es parseable como URL estándar de navegador, buscar por prefijo plano
      if (url.includes('register/')) {
        const token = url.split('register/')[1]?.split('?')[0];
        handleNavigate('register', { token });
      } else if (url.includes('receipt/')) {
        const hash = url.split('receipt/')[1]?.split('?')[0];
        handleNavigate('receipt', { receiptHash: hash });
      }
    }
  };

  useEffect(() => {
    // 1. Obtener URL inicial si la app fue lanzada por un Deep Link
    Linking.getInitialURL().then((url) => {
      if (url) handleDeepLink(url);
    });

    // 2. Suscribirse a eventos de enlaces mientras la app está abierta en segundo plano
    const subscription = Linking.addEventListener('url', (event) => {
      handleDeepLink(event.url);
    });

    return () => {
      subscription.remove();
    };
  }, []);

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar style="auto" />
      <View style={styles.content}>
        {currentScreen === 'home' && <HomePortalScreen onNavigate={handleNavigate} />}

        {currentScreen === 'register' && (
          <VoterRegistrationScreen
            initialToken={screenParams.token || ''}
            onNavigate={handleNavigate}
          />
        )}

        {currentScreen === 'booth' && <MobileBallotBoothScreen onNavigate={handleNavigate} />}

        {currentScreen === 'receipt' && (
          <MobileReceiptVerifierScreen
            initialReceiptHash={screenParams.receiptHash || ''}
            initialElectionId={screenParams.electionId || ''}
            onNavigate={handleNavigate}
          />
        )}

        {currentScreen === 'faq' && <MobileFaqAssistantScreen onNavigate={handleNavigate} />}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F8F7F4',
  },
  content: {
    flex: 1,
  },
});
