# Publicación académica desde JERS

La publicación utiliza una instancia EC2 t3.small con créditos de CPU Standard, disco gp3 cifrado de 20 GB, PostgreSQL con TLS interno, API, planificador y Caddy con HTTPS automático. La administración y los despliegues usan SSM, sin SSH público. CloudFront no pudo publicarse porque AWS exige verificar la cuenta con soporte; no se solicitó cambiar al plan de pago.

El nombre público se guarda en `/votoseguro/JERS/public-host` y usa sslip.io con la IPv4 de la instancia. Si se detiene y arranca EC2, su IPv4 puede cambiar: actualizar ese parámetro y desplegar otra vez, o configurar un dominio propio. Los puertos públicos son 80 (redirección y validación de certificados) y 443 (HTTPS).

La cuenta permanece en el plan FREE. El usuario autorizó consumir sus créditos gratuitos, sin convertirla al plan de pago. Estos recursos consumen créditos y no son gratuitos permanentemente. Eliminar los recursos al terminar el semestre; eliminar la instancia también elimina su disco y sus datos si no se exportan antes. No se desplegó la arquitectura de `infra/aws`, que incluye servicios adicionales.

Los cambios en JERS ejecutan las pruebas de GitHub Actions y, si pasan, despliegan esa revisión mediante OIDC y SSM. No se necesitan claves de AWS guardadas en GitHub. El servidor conserva PostgreSQL entre actualizaciones. Esta instalación académica de un solo servidor no ofrece alta disponibilidad.

Los secretos viven en parámetros SecureString de SSM en us-east-1: `/votoseguro/JERS/runtime`, `/votoseguro/JERS/origin-secret` y `/votoseguro/JERS/admin-password`. El usuario inicial es `admin@votoseguro.org`; su contraseña se consulta en el último parámetro con una identidad autorizada. Los archivos privados descargados al servidor tienen permisos restringidos.

Claude se configura con `AI_PROVIDER=ANTHROPIC` y `ANTHROPIC_API_KEY` en el servidor. Las respuestas estructuradas se validan y los errores del proveedor producen una respuesta de respaldo identificada. La clave nunca forma parte del frontend.

El OCR procesa las fotografías en el navegador con Tesseract y recursos del mismo sitio. Comprueba que los recursos existan, limita la espera inicial y reintenta la lectura de imágenes difíciles. Prueba giros de 0°, 90°, 180° y 270° y dos distribuciones de texto; compara confianza, etiquetas del documento y palabras legibles, y rechaza fragmentos de baja calidad. Solo el texto revisado pasa a la extracción del backend; los números devueltos por IA se contrastan con el texto observado. La biometría es un flujo separado que requiere consentimiento explícito antes de enviar imágenes al proveedor.
