import { test, expect } from '@playwright/test';
import { fileURLToPath } from 'node:url';

test('reads actual pixels and sends only reviewed text when the user requests extraction', async ({ page }) => {
  const writes: string[] = [];
  const externalRequests: string[] = [];
  page.on('request', request => {
    if (request.method() === 'POST') writes.push(request.postData() || '');
    const host = new URL(request.url()).hostname;
    const siteFont = ['fonts.googleapis.com', 'fonts.gstatic.com'].includes(host) && ['stylesheet', 'font'].includes(request.resourceType());
    if (!request.url().startsWith('http://127.0.0.1') && !request.url().startsWith('data:') && !siteFont) externalRequests.push(request.url());
  });
  await page.route('**/api/v1/ai/id-card/extract', async route => {
    const body = route.request().postDataJSON();
    expect(Object.keys(body).sort()).toEqual(['election_id', 'raw_ocr_text']);
    expect(body.raw_ocr_text).toContain('9123456');
    expect(body.raw_ocr_text).toContain('ANA');
    expect(body.raw_ocr_text).not.toContain('8001002');
    await route.fulfill({ json: { ci: '9123456', nombres: 'ANA', apellidos: 'ROJAS', regex_valid: true, requires_voter_confirmation: true, confidence_note: 'Revise los campos.', ai_source: 'DETERMINISTIC_FALLBACK' } });
  });
  await page.goto('/vote');
  await page.waitForLoadState('networkidle');
  externalRequests.length = 0;
  await page.getByRole('button', { name: /Escanear OCR/ }).click();
  const upload = page.getByLabel('Fotografía de la cédula');
  await upload.setInputFiles(fileURLToPath(new URL('./fixtures/id-card-test.png', import.meta.url)));
  await expect(page.locator('textarea')).toHaveValue(/9123456/, { timeout: 90_000 });
  expect(writes).toEqual([]);
  expect(externalRequests).toEqual([]);
  await page.getByRole('button', { name: /Extraer Campos/ }).click();
  await expect(page.getByText('9123456', { exact: true })).toBeVisible();
  expect(writes).toHaveLength(1);
  expect(writes[0]).not.toContain('data:image');
  await expect(page.getByPlaceholder('Ej. CI-8001001')).toHaveValue('');
  await page.getByRole('button', { name: /Confirmar mis datos/ }).click();
  await expect(page.getByPlaceholder('Ej. CI-8001001')).toHaveValue('9123456');
});

test('rejects invalid files without filling demo data', async ({ page }) => {
  await page.goto('/vote');
  await page.getByRole('button', { name: /Escanear OCR/ }).click();
  await page.getByLabel('Fotografía de la cédula').setInputFiles({ name: 'invalid.txt', mimeType: 'text/plain', buffer: Buffer.from('not an image') });
  await expect(page.getByText('Use una imagen JPG, PNG o WebP.')).toBeVisible();
  await expect(page.locator('textarea')).toHaveValue('');
});

test('reads a low contrast document using actual image preprocessing', async ({ page }) => {
  await page.goto('/vote');
  const image = await page.evaluate(async () => {
    const canvas=document.createElement('canvas'); canvas.width=1600; canvas.height=900;
    const ctx=canvas.getContext('2d')!;
    ctx.fillStyle='#ddd';ctx.fillRect(0,0,1600,900);
    ctx.fillStyle='#888';ctx.font='52px Arial';
    ['CEDULA DE IDENTIDAD','NUMERO: 7654321','NOMBRES: MARIA','APELLIDOS: LOPEZ'].forEach((line,index)=>ctx.fillText(line,70,130+index*140));
    return canvas.toDataURL('image/png').split(',')[1];
  });
  await page.getByRole('button',{name:/Escanear OCR/}).click();
  await page.getByLabel('Fotografía de la cédula').setInputFiles({name:'low-contrast.png',mimeType:'image/png',buffer:Buffer.from(image,'base64')});
  await expect(page.locator('textarea')).toHaveValue(/7654321/, {timeout:90_000});
});

test('reports a missing OCR runtime rather than spinning forever', async ({page}) => {
  await page.route('**/ocr/worker.min.js', route => route.fulfill({status:404,body:'missing'}));
  await page.goto('/vote');
  await page.getByRole('button',{name:/Escanear OCR/}).click();
  await page.getByLabel('Fotografía de la cédula').setInputFiles(fileURLToPath(new URL('./fixtures/id-card-test.png',import.meta.url)));
  await expect(page.getByText(/El escáner no pudo cargar sus archivos/)).toBeVisible();
  await expect(page.getByLabel('Fotografía de la cédula')).toBeEnabled();
});
