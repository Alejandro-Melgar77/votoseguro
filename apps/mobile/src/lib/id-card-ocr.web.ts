export async function scanIdCard(_source: 'camera' | 'library'): Promise<string | null> {
  throw new Error('Use la aplicación Android/iOS o el escáner del portal web para leer una fotografía.');
}
