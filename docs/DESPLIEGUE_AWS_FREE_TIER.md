# Despliegue en AWS (capa gratuita) — rama `JERS`

> **AVISO: este documento describe un despliegue anterior. Sus direcciones y credenciales de prueba NO corresponden al AWS actual.**
>
> Acceso vigente: **https://votoseguro-3-239-171-45.sslip.io/login**. El usuario inicial es `admin@votoseguro.org`, con la contraseña privada guardada en SSM (`/votoseguro/JERS/admin-password`), no la contraseña pública de ejemplo de este documento. La configuración actual se explica en [AWS_JERS.md](AWS_JERS.md).
>
> `https://votoseguro.pages.dev` sigue apuntando a la API anterior de Render y no comparte las cuentas de AWS. Los usuarios y votantes demo que aparecen debajo pertenecen al despliegue histórico; no prueban la existencia de esas cuentas en el servidor actual.

## Registro histórico — no usar estas instrucciones para el AWS actual

## 1. URL única

**https://32-197-219-229.sslip.io**

Certificado válido de Let's Encrypt (sin aviso de "conexión no segura"). Cualquier acceso por
`http://`, por la IP `32.197.219.229` o por `ec2-32-197-219-229.compute-1.amazonaws.com`
redirige automáticamente a esa URL.

| Página | Ruta |
|---|---|
| Página principal (solicitud de elecciones) | `/` |
| Ingreso de administradores y observadores | `/login` |
| Cabina de votación | `/vote` |
| Verificar comprobante | `/verify-receipt` |
| Portal público de auditoría | `/audit-portal` |
| Manual de usuario | `/manual` |
| Estado del sistema | `/health` |
| API (Swagger) | `/docs` |

> `sslip.io` es un DNS público gratuito que resuelve `32-197-219-229.sslip.io` a la IP del EC2.
> CloudFront no se usa porque AWS exige verificar la cuenta (ticket a soporte) antes de crear
> distribuciones. Si la IP del EC2 cambia (detener e iniciar la instancia), la URL cambia a
> `<nueva-ip-con-guiones>.sslip.io` y `update.sh` emite el certificado nuevo solo.

## 2. Usuarios de prueba históricos — no válidos para el AWS actual

| Rol | Correo | Contraseña |
|---|---|---|
| Operador de plataforma | admin@votoseguro.org | AdminPlatform2026! |
| Admin general (U. EL GRAN ESTUDIO) | admin@granestudio.edu.bo | GranEstudio2026! |
| Delegado de segmento (FICCT) | delegado.ficct@granestudio.edu.bo | Delegado2026! |
| Observador (solo lectura: monitoreo, resultados, integridad) | observador@granestudio.edu.bo | UsuarioComun2026! |
| Admin general (Ecuador) | admin@cne.gob.ec | Ecuador2026! |

### Votantes (cabina `/vote`)

La votación de "Elecciones Generales Universitarias 2026" está abierta. Cada credencial sirve
para **un solo voto**; el admin general ve todas en *Padrón → Credenciales Demo*.

| Votante | CI | Credencial |
|---|---|---|
| José Rodríguez | CI-8001001 | VS-5AEA-YBGX-UWM8 |
| Alejandro Melgar Suárez | CI-8001003 | VS-ULXE-C6GE-9T25 |
| Valeria Paz Justiniano | CI-8001004 | VS-DTDE-7Q8M-VM5F |
| Rodrigo Chávez Méndez | CI-8001005 | VS-MWC7-27DZ-STV9 |
| Camila Flores Torrico | CI-8001006 | VS-YM6N-QBRY-X2JJ |

## 3. Arquitectura (sin cargos)

Un único EC2 `t3.micro` (capa gratuita) con 2 GB de swap:

- **nginx**: HTTPS (Let's Encrypt, renovación automática con `votoseguro-certbot.timer`),
  sirve el frontend React y hace proxy de `/api` (incluye WebSocket) a la API.
- **Docker Compose** (`infra/aws/server/docker-compose.prod.yml`): PostgreSQL 16 y API FastAPI.
  Al arrancar aplica migraciones y el seed idempotente.
- **S3** (`votoseguro-web-<cuenta>`): artefactos compilados del frontend.
- **SSM**: administración sin SSH.
- Secretos en `/opt/votoseguro/.env` del servidor (no en el repositorio).

OCR: corre en el navegador (Tesseract, archivos servidos desde `/ocr`), la foto no sale del
dispositivo; el backend solo recibe el texto.

IA local: el servidor está con `AI_LOCAL_ENABLED=false` y usa reglas deterministas. Para usar el
modelo local, en la PC con Ollama ejecute `INICIAR_IA_LOCAL.bat` (túnel ngrok) y en el servidor
ponga `AI_LOCAL_ENABLED=true` en `/opt/votoseguro/.env` y vuelva a ejecutar `update.sh`.

## 4. Actualizar desde GitHub

Desde la PC (con credenciales AWS en variables de entorno o perfil):

```bash
python scripts/deploy_aws_free_tier.py --skip-stack
```

Compila el frontend, lo sube a S3 y ejecuta en el EC2 (vía SSM)
`infra/aws/server/update.sh`, que hace `git reset` a `origin/JERS`, reconstruye la API,
sincroniza el frontend y renueva nginx/HTTPS.

Solo backend (desde *Systems Manager → Run Command → AWS-RunShellScript*):

```bash
bash /opt/votoseguro/app/infra/aws/server/update.sh
```

Logs: `docker logs --tail 100 votoseguro-api`.

## 5. Apagar todo al terminar

```bash
aws s3 rm s3://votoseguro-web-<cuenta> --recursive
aws cloudformation delete-stack --stack-name votoseguro-free-tier --region us-east-1
```
