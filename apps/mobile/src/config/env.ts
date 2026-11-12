/**
 * Configuración de entorno para la aplicación móvil VotoSeguro.
 */

declare const process: {
  env: {
    EXPO_PUBLIC_API_URL?: string;
    [key: string]: string | undefined;
  };
};

export const ENV = {
  API_BASE_URL:
    (typeof process !== 'undefined' && process.env && process.env.EXPO_PUBLIC_API_URL) ||
    'https://votoseguro-api-plyu.onrender.com/api/v1',
  APP_NAME: 'VotoSeguro Mobile v2.0',
  DEEP_LINK_SCHEME: 'votoseguro://',
};
