import { createWorker, PSM } from 'tesseract.js';

type Reading = { text: string; confidence: number };
function quality(data: Reading) {
  const normalized = data.text.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toUpperCase();
  const labels = normalized.match(/\b(CEDULA|IDENTIDAD|NOMBRES?|APELLIDOS?|NACIMIENTO|BOLIVIA|PLURINACIONAL|NUMERO)\b/g) || [];
  const words = normalized.match(/\b[A-Z]{3,}\b/g) || [];
  const hasNumber = /\b\d{5,10}\b/.test(normalized);
  return {
    score: data.confidence + Math.min(labels.length, 5) * 14 + Math.min(words.length, 10) * 2 + (hasNumber ? 12 : 0),
    good: data.confidence >= 65 && labels.length >= 2 && words.length >= 4 && hasNumber,
    readable: data.confidence >= 45 && words.length >= 4 && (labels.length > 0 || data.confidence >= 75),
  };
}

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
      let best: Reading = { text: '', confidence: 0 };
      const rotated = document.createElement('canvas');
      try {
        // rotateAuto deskews text; it does not reliably correct upside-down cards.
        // Rotate the pixels explicitly, retaining only the best readable orientation.
        orientations: for (const degrees of [0, 90, 180, 270]) {
          const sideways = degrees === 90 || degrees === 270;
          rotated.width = sideways ? canvas.height : canvas.width;
          rotated.height = sideways ? canvas.width : canvas.height;
          const output = rotated.getContext('2d');
          if (!output) throw new Error('No se pudo preparar la imagen.');
          output.translate(rotated.width / 2, rotated.height / 2);
          output.rotate(degrees * Math.PI / 180);
          output.drawImage(canvas, -canvas.width / 2, -canvas.height / 2);
          for (const mode of [PSM.AUTO, PSM.SPARSE_TEXT]) {
            await worker.setParameters({ tessedit_pageseg_mode: mode });
            const result = await worker.recognize(rotated, { rotateAuto: true });
            if (quality(result.data).score > quality(best).score) best = result.data;
            if (quality(best).good) break orientations;
          }
        }
      } finally {
        rotated.width = 0;
        rotated.height = 0;
      }
      const text = best.text.trim();
      if (!text || !quality(best).readable) {
        throw new Error('No se pudo leer el carnet con suficiente claridad. Fotografíe solo el documento completo, de frente, con buena luz y sin reflejos. También puede escribir los datos manualmente.');
      }
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
