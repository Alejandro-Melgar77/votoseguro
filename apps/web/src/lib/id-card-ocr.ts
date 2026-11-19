import { createWorker } from 'tesseract.js';

export async function recognizeIdCard(file: File, progress: (value: number) => void): Promise<string> {
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
    throw new Error('Use una imagen JPG, PNG o WebP.');
  }
  if (file.size > 10 * 1024 * 1024) throw new Error('La imagen no debe superar 10 MB.');
  const bitmap = await createImageBitmap(file);
  const canvas = document.createElement('canvas');
  try {
    const scale = Math.min(1, 2400 / Math.max(bitmap.width, bitmap.height));
    canvas.width = Math.round(bitmap.width * scale);
    canvas.height = Math.round(bitmap.height * scale);
    const ctx = canvas.getContext('2d');
    if (!ctx) throw new Error('No se pudo abrir la imagen.');
    ctx.fillStyle = '#fff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    const root = `${import.meta.env.BASE_URL}ocr`;
    const worker = await createWorker('spa', 1, {
      workerPath: `${root}/worker.min.js`,
      corePath: `${root}/core`,
      langPath: `${root}/lang`,
      cacheMethod: 'none',
      logger: (event) => { if (event.status === 'recognizing text') progress(event.progress); },
    });
    try {
      const result = await worker.recognize(canvas);
      const text = result.data.text.trim();
      if (!text) throw new Error('No se detectó texto. Tome otra foto con buena luz y sin reflejos.');
      return text;
    } finally {
      await worker.terminate();
    }
  } finally {
    bitmap.close();
    canvas.width = 0;
    canvas.height = 0;
  }
}
