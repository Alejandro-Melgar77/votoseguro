import React, { createContext, useContext, useState, useEffect, useMemo } from 'react';
import esTranslations from './locales/es.json';
import quTranslations from './locales/qu.json';
import ayTranslations from './locales/ay.json';
import gnTranslations from './locales/gn.json';

export type LanguageCode = 'es' | 'qu' | 'ay' | 'gn';

export interface LanguageOption {
  code: LanguageCode;
  label: string;
  native: string;
  flag: string;
  isNativeReviewed: boolean;
}

export const SUPPORTED_LANGUAGES: LanguageOption[] = [
  { code: 'es', label: 'Español', native: 'Español', flag: '🇪🇸', isNativeReviewed: true },
  { code: 'qu', label: 'Quechua', native: 'Runasimi', flag: '🏔️', isNativeReviewed: false },
  { code: 'ay', label: 'Aymara', native: 'Aymar Aru', flag: '☀️', isNativeReviewed: false },
  { code: 'gn', label: 'Guaraní', native: "Avañe'ẽ", flag: '🌿', isNativeReviewed: false },
];

const TRANSLATION_MAP: Record<LanguageCode, any> = {
  es: esTranslations,
  qu: quTranslations,
  ay: ayTranslations,
  gn: gnTranslations,
};

interface I18nContextType {
  language: LanguageCode;
  setLanguage: (lang: LanguageCode) => void;
  t: (keyPath: string, fallback?: string) => string;
  currentLanguageOption: LanguageOption;
  isNativeReviewed: boolean;
  reviewDisclaimer: string;
}

const I18nContext = createContext<I18nContextType | null>(null);

const STORAGE_KEY = 'votoseguro_language_preference';

export const I18nProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [language, setLanguageState] = useState<LanguageCode>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY) as LanguageCode | null;
      if (saved && ['es', 'qu', 'ay', 'gn'].includes(saved)) {
        return saved;
      }
    } catch {
      // Ignorar fallback
    }
    return 'es';
  });

  const setLanguage = (lang: LanguageCode) => {
    setLanguageState(lang);
    try {
      localStorage.setItem(STORAGE_KEY, lang);
    } catch {
      // Ignorar fallback
    }
  };

  const currentLanguageOption = useMemo(() => {
    return SUPPORTED_LANGUAGES.find((l) => l.code === language) || SUPPORTED_LANGUAGES[0];
  }, [language]);

  const activeDictionary = useMemo(() => {
    return TRANSLATION_MAP[language] || TRANSLATION_MAP.es;
  }, [language]);

  const t = (keyPath: string, fallback?: string): string => {
    const keys = keyPath.split('.');
    let current: any = activeDictionary;
    for (const k of keys) {
      if (current && typeof current === 'object' && k in current) {
        current = current[k];
      } else {
        current = undefined;
        break;
      }
    }

    if (typeof current === 'string') {
      return current;
    }

    // Fallback al español si falta en el idioma seleccionado
    if (language !== 'es') {
      let fallbackCurrent: any = TRANSLATION_MAP.es;
      for (const k of keys) {
        if (fallbackCurrent && typeof fallbackCurrent === 'object' && k in fallbackCurrent) {
          fallbackCurrent = fallbackCurrent[k];
        } else {
          fallbackCurrent = undefined;
          break;
        }
      }
      if (typeof fallbackCurrent === 'string') {
        return fallbackCurrent;
      }
    }

    return fallback || keyPath;
  };

  const isNativeReviewed = currentLanguageOption.isNativeReviewed;
  const reviewDisclaimer = isNativeReviewed
    ? ''
    : `Traducción asistida por Gemini (${currentLanguageOption.native}) — Pendiente de revisión final por hablante nativo.`;

  return (
    <I18nContext.Provider
      value={{
        language,
        setLanguage,
        t,
        currentLanguageOption,
        isNativeReviewed,
        reviewDisclaimer,
      }}
    >
      {children}
    </I18nContext.Provider>
  );
};

export const useI18n = (): I18nContextType => {
  const context = useContext(I18nContext);
  if (!context) {
    // Modo seguro sin proveedor: fallback al español
    return {
      language: 'es',
      setLanguage: () => {},
      t: (keyPath: string, fallback?: string) => fallback || keyPath,
      currentLanguageOption: SUPPORTED_LANGUAGES[0],
      isNativeReviewed: true,
      reviewDisclaimer: '',
    };
  }
  return context;
};
