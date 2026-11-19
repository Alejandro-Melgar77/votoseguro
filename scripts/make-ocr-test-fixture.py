"""Generate a synthetic identity card exclusively for OCR regression tests."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parent.parent
output = root / 'apps/web/tests/fixtures/id-card-test.png'
output.parent.mkdir(parents=True, exist_ok=True)
image = Image.new('RGB', (1600, 900), 'white')
draw = ImageDraw.Draw(image)
font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 52)
for index, line in enumerate([
    'DOCUMENTO SINTETICO PARA PRUEBAS', 'CEDULA DE IDENTIDAD',
    'NUMERO: 9123456', 'NOMBRES: ANA', 'APELLIDOS: ROJAS',
    'FECHA DE NACIMIENTO: 14/05/2001',
]):
    draw.text((70, 80 + index * 105), line, font=font, fill='black')
image.save(output)
