/**
 * Configuración de entorno para la aplicación móvil VotoSeguro.
 */

declare const process: {
  env: {
    EXPO_PUBLIC_API_URL?: string;
    [key: string]: string | undefined;
  };
};

const configuredApi = process.env.EXPO_PUBLIC_API_URL;
if (!configuredApi && typeof __DEV__ !== 'undefined' && !__DEV__) {
  throw new Error('Configure EXPO_PUBLIC_API_URL antes de compilar la aplicación de producción.');
}

export const ENV = {
  API_BASE_URL:
    configuredApi || 'http://10.0.2.2:8000/api/v1',
  APP_NAME: 'VotoSeguro Mobile v2.0',
  DEEP_LINK_SCHEME: 'votoseguro://',
};
