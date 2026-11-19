# Despliegue de VotoSeguro en AWS

La infraestructura está preparada con Terraform en `infra/aws`. Crear los recursos y publicar requiere una cuenta AWS, un dominio de API y un certificado ACM validado en la región elegida. Esta preparación no crea recursos en la cuenta.

## Arquitectura

- Frontend React y motor OCR servidos desde S3 privado mediante CloudFront con HTTPS. Las rutas de la SPA se resuelven con una función de CloudFront.
- API en ECS Fargate detrás de ALB HTTPS y WAF. Dos tareas por defecto, en subredes privadas de dos zonas.
- Scheduler como servicio Fargate separado. La API no inicia schedulers adicionales.
- RDS PostgreSQL 16 privado, cifrado, TLS con verificación del certificado, Multi-AZ y 14 días de respaldos.
- Redis privado con TLS, autenticación y réplica para compartir los límites de solicitudes entre tareas de API.
- Secretos en Secrets Manager; imágenes versionadas e inmutables en ECR; registros y alarmas en CloudWatch.
- Dos NAT Gateways, una por zona, para salida desde los servicios privados. Esta configuración genera costos recurrentes desde `terraform apply`.

El endpoint y el nombre del modelo local se conservan como parámetros. No se cambia el modelo ni se provisiona un servidor de inferencia nuevo.

## Requisitos

Instale AWS CLI, Docker con daemon iniciado, Node 22, pnpm 11.25.0, Terraform 1.11.4 y RTK. Inicie sesión con un perfil AWS autorizado para crear la infraestructura. El certificado de `api_domain` debe existir en ACM en la misma región que ALB. Si utiliza Route 53, indique el ID de zona; con otro proveedor DNS, cree el CNAME hacia `api_dns_target` que devuelve Terraform.

Desde la raíz del repositorio, copie `infra/aws/terraform.tfvars.example` a `infra/aws/terraform.tfvars`. Complete región, dominio, ARN del certificado, correo administrativo y endpoint de IA existente. No guarde credenciales AWS ni claves API en ese archivo.

Los archivos de estado de Terraform contienen material sensible generado. El directorio los excluye de Git. Para un equipo, configure un backend S3 con cifrado, bloqueo de estado, versionado y permisos restringidos antes de crear los recursos. El backend no se crea automáticamente: use un bucket de estado administrado por el equipo y un archivo `backend.tf` con `backend "s3" {}` y sus parámetros en `terraform init -backend-config=...`.

## Primera instalación

1. Revise el plan, sin crear recursos:

   ```powershell
   rtk proxy powershell -NoProfile -File scripts/deploy-aws.ps1 -Phase Plan -AwsProfile su-perfil
   ```

2. Cree la infraestructura con API y scheduler aún detenidos:

   ```powershell
   rtk proxy powershell -NoProfile -File scripts/deploy-aws.ps1 -Phase Infrastructure -AwsProfile su-perfil
   ```

   Terraform muestra los cambios y pide confirmar su aplicación. RDS y ALB tienen protección contra borrado. El aprovisionamiento puede tardar varios minutos.

3. Consulte `app_secret_arn` en las salidas de Terraform. En Secrets Manager, complete `GEMINI_API_KEY`, `SMTP_USER` y `SMTP_PASSWORD` si usa esas funciones. Conserve las claves ya generadas para JWT, nullifiers, Redis y administración. No cambie `NULLIFIER_SECRET` durante una elección. Para correo SES, verifique el remitente y el acceso de envío de la cuenta.

4. Complete el registro DNS de la API y espere a que resuelva. Publique una versión con etiqueta nueva, preferentemente el SHA del commit:

   ```powershell
   rtk proxy powershell -NoProfile -File scripts/deploy-aws.ps1 -Phase Release -Tag VERSION_UNICA -AwsProfile su-perfil
   ```

   El script construye la imagen Linux, la sube a ECR, registra las definiciones de tarea, ejecuta `alembic upgrade head` en una tarea aislada y exige salida exitosa. Después activa los servicios, comprueba estabilidad y salud de la API, compila el frontend con la URL real, lo sube a S3 e invalida la caché de CloudFront. Una migración fallida impide actualizar los servicios. El circuito de despliegue de ECS revierte las tareas que no arrancan correctamente.

5. Conserve `image_tag = "VERSION_UNICA"` y `service_enabled = true` en su archivo local `terraform.tfvars` antes de ejecutar futuros planes. No repita la fase Infrastructure sobre un servicio activo: esa fase inicial fuerza el número de tareas a cero.

La contraseña inicial del operador está en `PLATFORM_ADMIN_PASSWORD` del secreto de aplicación. No existe contraseña pública de producción. El sembrado de instituciones demo y el inspector de credenciales están desactivados en producción.

## Operación

- Si rota los secretos de aplicación, fuerce un nuevo despliegue de ambos servicios: ECS inyecta los secretos al iniciar cada tarea. RDS administra y rota su contraseña maestra; la API y el scheduler recuperan el secreto vigente al abrir conexiones y lo refrescan si RDS rechaza una contraseña anterior. La tarea de migraciones recibe el valor vigente al iniciarse.
- Confirme la suscripción SNS del correo de alarmas. Se incluyen alarmas por tareas no saludables y espacio disponible de RDS.
- El monitoreo en vivo utiliza conexiones WebSocket por proceso y mantiene respaldo mediante consultas HTTP; para distribución instantánea de eventos entre réplicas se necesita un bus de publicación adicional. Los límites HTTP sí se comparten con Redis.
- Antes de cada elección de producción, realice la ceremonia de claves estando en DRAFT, entregue cada fragmento a su custodio y oculte los fragmentos de la pantalla. No se guardan ni se pueden recuperar desde la API. La publicación y recepción de votos exigen ceremonia previa en producción.
- El almacenamiento de votos conserva los cifrados sin candidato ni tipo de selección legibles. Los resultados de una elección cifrada permanecen bloqueados hasta el escrutinio con quórum. El servidor sigue siendo parte del perímetro de confianza durante la recepción y el escrutinio.

## Bases anteriores de demostración

La migración `0008_private_ballots` rechaza bases que ya contengan votos Paillier con selecciones legibles. No reescribe esos votos ni recalcula hashes, porque eso invalidaría la evidencia publicada. Conserve la base anterior como archivo de demostración y utilice una base nueva para producción. Los antiguos fragmentos de ejemplo no constituyen custodia segura.

## App móvil

Configure `EXPO_PUBLIC_API_URL=https://SU_DOMINIO_API/api/v1` en el entorno de compilación de Expo/EAS. La aplicación requiere una compilación nativa: ML Kit y el reconocedor de voz no están incluidos en Expo Go. iOS requiere 15.5 o posterior. Android necesita un servicio y paquete de español compatibles con reconocimiento sin conexión.

```powershell
rtk proxy pnpm --filter @votoseguro/mobile android
# En macOS, para iOS:
rtk proxy pnpm --filter @votoseguro/mobile ios
```

Se incluye `apps/mobile/eas.json` para generar un APK interno y una compilación de producción con una cuenta Expo propia. Las imágenes elegidas para OCR se leen con ML Kit y se elimina la copia temporal del selector. No se suben imágenes al endpoint de OCR. El texto se muestra primero para revisión y el CI se aplica solo al confirmar.

Los parches versionados de `expo-speech-recognition` y `expo-speech` impiden la caída silenciosa a reconocimiento remoto en iOS y excluyen voces Android que requieren red. Si falta reconocimiento o voz local, debe instalarse el paquete del dispositivo o continuar con los controles de pantalla; no se sustituye por audio remoto.

## Verificación realizada en esta preparación

- 58 pruebas backend aprobadas, con regresiones sobre votos sin selección legible, entrega única de fragmentos, bloqueo de reconfiguración, requisitos de producción y rotación de contraseña RDS.
- Pruebas Playwright con lectura real de píxeles en Chrome, confirmación del CI y rechazo de archivos inválidos.
- Compilación de frontend, comprobación de tipos móvil, configuración de prebuild y generación del bundle Android.
- Construcción de la imagen Linux del backend, aplicación de las ocho migraciones en PostgreSQL 16 y arranque del contenedor con comprobación de salud HTTP 200.
- `terraform init -backend=false`, `terraform fmt` y `terraform validate` sin crear recursos.
- Workflow GitHub Actions que verifica migraciones sobre PostgreSQL 16, pruebas, compilación de imagen, navegador y Terraform.

Las compilaciones nativas Android/iOS y las pruebas de cámara/micrófono deben completarse en dispositivos físicos. Validar Terraform no sustituye un plan autenticado en la cuenta AWS ni una prueba de carga del entorno publicado; no se declara un resultado de carga que no se haya ejecutado.

## Referencias técnicas

- [Secretos de ECS](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/secrets-envvar-secrets-manager.html)
- [Tesseract.js](https://github.com/naptha/tesseract.js)
- [ML Kit para React Native](https://github.com/a7med-mahmoud/react-native-ml-kit/tree/main/text-recognition)
- [Reconocimiento de voz para Expo](https://github.com/jamsch/expo-speech-recognition)
