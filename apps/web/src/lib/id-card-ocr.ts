import { createWorker, PSM } from 'tesseract.js';

export async function recognizeIdCard(file: File, progress: (value: number) => void): Promise<string> {
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type) && !/\.(jpe?g|png|webp)$/i.test(file.name)) {
    throw new Error('Use una imagen JPG, PNG o WebP.');
  }
  if (file.size > 10 * 1024 * 1024) throw new Error('La imagen no debe superar 10 MB.');
  const bitmap = await createImageBitmap(file);
  const canvas = document.createElement('canvas');
  try {
    // Small camera images need enlargement; large images must not exhaust mobile memory.
    const scale = Math.min(3, Math.max(1600, Math.min(2600, Math.max(bitmap.width, bitmap.height))) / Math.max(bitmap.width, bitmap.height));
    canvas.width = Math.round(bitmap.width * scale);
    canvas.height = Math.round(bitmap.height * scale);
    const ctx = canvas.getContext('2d');
    if (!ctx) throw new Error('No se pudo abrir la imagen.');
    ctx.fillStyle = '#fff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.filter = 'grayscale(1) contrast(1.3)';
    ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    const root = `${import.meta.env.BASE_URL}ocr`;
    for (const asset of ['worker.min.js', 'lang/spa.traineddata.gz']) {
      const response = await fetch(`${root}/${asset}`, { method: 'HEAD', signal: AbortSignal.timeout(15_000) });
      if (!response.ok || response.headers.get('content-type')?.includes('text/html')) {
        throw new Error('El escáner no pudo cargar sus archivos. Recargue la página; si continúa, avise al administrador del despliegue.');
      }
    }
    let timer: ReturnType<typeof setTimeout> | undefined;
    const deadline = new Promise<never>((_, reject) => {
      timer = setTimeout(() => reject(new Error('El motor OCR tardó demasiado en cargar. Compruebe la conexión y vuelva a intentar.')), 60_000);
    });
    const worker = await Promise.race([createWorker('spa', 1, {
      workerPath: `${root}/worker.min.js`,
      corePath: `${root}/core`,
      langPath: `${root}/lang`,
      cacheMethod: 'none',
      logger: (event) => { if (event.status === 'recognizing text') progress(event.progress); },
    }), deadline]).finally(() => { if (timer) clearTimeout(timer); });
    try {
      await worker.setParameters({ tessedit_pageseg_mode: PSM.AUTO });
      const first = await worker.recognize(canvas, { rotateAuto: true });
      let best = first.data;
      if (best.confidence < 65 || !/\d{5,10}/.test(best.text)) {
        // A second layout pass handles cards with a portrait and scattered labels.
        await worker.setParameters({ tessedit_pageseg_mode: PSM.SPARSE_TEXT });
        const second = await worker.recognize(canvas, { rotateAuto: true });
        const score = (data: typeof best) => data.confidence + (/\d{5,10}/.test(data.text) ? 30 : 0);
        if (score(second.data) > score(best)) best = second.data;
      }
      const text = best.text.trim();
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
