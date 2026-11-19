import { createRequire } from 'node:module';
import { mkdir, cp, writeFile, access } from 'node:fs/promises';
import { dirname, join } from 'node:path';
const require = createRequire(import.meta.url);
const output = new URL('../public/ocr/', import.meta.url);
await mkdir(new URL('core/', output), { recursive: true });
await mkdir(new URL('lang/', output), { recursive: true });
const tesseract = dirname(require.resolve('tesseract.js/package.json'));
const core = dirname(require.resolve('tesseract.js-core/package.json'));
await cp(join(tesseract, 'dist/worker.min.js'), new URL('worker.min.js', output));
await cp(core, new URL('core/', output), { recursive: true });
const language = new URL('lang/spa.traineddata.gz', output);
try { await access(language); } catch {
  const response = await fetch('https://raw.githubusercontent.com/naptha/tessdata/gh-pages/4.0.0/spa.traineddata.gz');
  if (!response.ok) throw new Error(`Descarga de OCR español: HTTP ${response.status}`);
  await writeFile(language, Buffer.from(await response.arrayBuffer()));
}
console.log('Motor OCR y datos de español preparados para servir desde el mismo sitio.');
