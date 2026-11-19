# OCR y accesibilidad por voz

## Web

El escáner acepta fotografías JPG, PNG y WebP de hasta 10 MB. Tesseract procesa los píxeles en un worker local, con datos de reconocimiento en español. El proceso de compilación prepara el worker, WebAssembly y datos de idioma para servirlos desde el propio sitio, sin descargar el motor de un tercero al escanear.

El texto reconocido se muestra para corregirlo. El botón de extracción envía únicamente ese texto al endpoint existente de campos de cédula; la fotografía no se envía. Antes de rellenar el formulario, el usuario confirma los campos extraídos. Una foto ilegible produce un mensaje de error y nunca se sustituye por una identidad de ejemplo.

Los comandos de voz web requieren un navegador compatible con `SpeechRecognition.processLocally` y el paquete español local. Si el navegador no permite procesamiento local, la captura se deshabilita y se mantienen los botones. La lectura elige una voz de español marcada como local por el navegador.

## Android e iOS

La cámara o galería proporciona la imagen a ML Kit en el dispositivo. Se elimina la copia temporal del selector tras reconocerla; el original elegido por el usuario no se elimina. Primero se revisa el texto, después se extraen los campos y finalmente se confirma el CI. La voz usa reconocimiento nativo local y síntesis del sistema con los parches incluidos en `patches/`.

Compile la app nativa con sus permisos de cámara, micrófono y reconocimiento. No funciona con Expo Go. Antes de habilitar voz, instale un modelo de español sin conexión y una voz española local. Pruebe lectura, selección de candidato, navegación, revisión y confirmación final en un teléfono real. La comprobación de tipos no acredita funcionamiento de los permisos ni calidad de reconocimiento del teléfono.

## Verificación facial opcional

Se retiró la generación de imágenes sintéticas del flujo de registro. El endpoint valida archivos de imagen reales y su tamaño antes de enviarlos al proveedor configurado, con consentimiento explícito. Si el proveedor no puede comparar los rostros, devuelve INCONCLUSIVE. Seleccionar la alternativa manual no verifica automáticamente la identidad: la activación debe completarse con credencial o revisión humana.

## Pruebas

```powershell
rtk proxy pnpm --filter @votoseguro/web test
rtk proxy pnpm --filter @votoseguro/web build
rtk proxy pnpm --filter @votoseguro/mobile check-types
```

La imagen de `apps/web/tests/fixtures` es un documento sintético exclusivo para regresión automatizada; no forma parte de los formularios de la aplicación. Las pruebas leen sus píxeles con el motor real y comprueban que ninguna imagen se incluya en solicitudes a la API.
