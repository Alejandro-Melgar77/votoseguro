# Guía de Despliegue en la Nube y Operación en Producción — VotoSeguro v3.0.0
**Arquitectura de Alta Disponibilidad, Criptografía Homomórfica e IA Híbrida**  
*Asignatura:* Ingeniería de Software I (INF 422 SB) — UAGRM  
*Versión:* `v3.0.0` (Release Final Certificado — Sprint 3)

---

## 1. Topología de Arquitectura en la Nube

VotoSeguro implementa una arquitectura desacoplada, multi-tenant y contenerizada diseñada para escalar bajo alta concurrencia electoral:

```mermaid
graph TD
    subgraph Clientes
        VoterWeb["Frontend Web (React + Vite)<br/>Vercel / Netlify"]
        VoterMobile["App Móvil (React Native + Expo)<br/>Android / iOS (EAS Build)"]
        Auditor["Portal Público de Auditoría<br/>Sin Autenticación (/audit-portal)"]
    end

    subgraph Backend & API Gateway
        FastAPI["API Backend (FastAPI + Python 3.11+)<br/>Render / Cloud Run (Docker)"]
        SlowAPI["Rate Limiting & Anti-DoS (SlowAPI)"]
    end

    subgraph Almacenamiento & Criptografía
        Postgres["PostgreSQL 15+ Managed<br/>Supabase / Cloud SQL"]
        Ledger["Ledger Inmutable Encadenado (SHA-256)"]
        Paillier["Motor Criptográfico Paillier (phe)"]
        Shamir["Custodia de Claves Shamir (k de n)"]
    end

    subgraph Capa de Inteligencia Artificial Híbrida
        LocalNode["Nodo Neuronal Local (LFM-3b)<br/>vLLM / Ollama / LM Studio"]
        Ngrok["Túnel Seguro HTTPS (ngrok)"]
        Gemini["Google Gemini 3.8 Flash<br/>(IA-E1 Resumen, IA-E2 Idiomas, IA-E3 Detección)"]
    end

    VoterWeb --> FastAPI
    VoterMobile --> FastAPI
    Auditor --> FastAPI
    FastAPI --> SlowAPI
    FastAPI --> Postgres
    FastAPI --> Ledger
    FastAPI --> Paillier
    FastAPI --> Shamir
    FastAPI -.->|IA-L1, IA-L2b, IA-L3, IA-L4| Ngrok
    Ngrok -.-> LocalNode
    FastAPI -.->|IA-E1, IA-E2, IA-E3| Gemini
```

---

## 2. Servicios Recomendados y Dimensionamiento

| Componente | Proveedor Recomendado | Nivel / Plan Mínimo | Justificación Técnica |
| :--- | :--- | :--- | :--- |
| **Base de Datos** | **Supabase** (PostgreSQL) | Pro / Compute Add-on | Conexiones `pgbouncer` para soportar 1,000 VUs concurrentes y pools asíncronos (`asyncpg`). |
| **Backend API** | **Render** / **Google Cloud Run** | Standard (2 GB RAM, 2 vCPU) | Operaciones matemáticas modulares Paillier ($n^2$ de 2048 bits) y manejo asíncrono con Uvicorn. |
| **Frontend Web** | **Vercel** / **Netlify** | Hobby / Pro | Despliegue estático global CDN (Edge Network) con tiempos de carga sub-segundo. |
| **App Móvil** | **Expo Application Services (EAS)** | Free / Production | Generación de APK / AAB para Android y compilación iOS. |
| **Nodo IA Local** | **Servidor Local / GPU On-Premise** | NVIDIA RTX 3060+ (8 GB VRAM) | Soberanía de datos de padrón e inferencia LFM-3b con baja latencia sin costes de tokens. |

---

## 3. Despliegue de la Base de Datos (Supabase PostgreSQL)

1. **Creación del Proyecto:**
   - Inicie sesión en [supabase.com](https://supabase.com) y cree un nuevo proyecto: `votoseguro-prod`.
   - Región recomendada: `sa-east-1` (São Paulo) o `us-east-1` para menor latencia con Bolivia.
2. **Obtención de la Cadena de Conexión:**
   - Vaya a **Project Settings -> Database -> Connection string**.
   - Seleccione el modo **URI (Transaction Pooler)** o **Session Pooler** (puerto `5432` o `6543`).
   - Formato requerido para SQLAlchemy asíncrono:
     ```text
     postgresql+asyncpg://postgres.[REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
     ```
3. **Migraciones y Esquema Inicial:**
   - Al iniciar el backend FastAPI, SQLAlchemy inicializa automáticamente todas las tablas mediante `Base.metadata.create_all` y Alembic.

---

## 4. Despliegue del Backend en Render

### 4.1 Archivo de Configuración `render.yaml`

El repositorio incluye la configuración lista para despliegue automático:

```yaml
services:
  - type: web
    name: votoseguro-api
    env: python
    region: ohio
    plan: standard
    buildCommand: "cd apps/api && pip install -r requirements.txt"
    startCommand: "cd apps/api && uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 4"
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.9
      - key: ENVIRONMENT
        value: production
      - key: DATABASE_URL
        sync: false
      - key: SECRET_KEY
        generateValue: true
      - key: GEMINI_API_KEY
        sync: false
      - key: GEMINI_MODEL
        value: gemini-3.8-flash
      - key: LOCAL_AI_BASE_URL
        sync: false
```

### 4.2 Variables de Entorno del Backend en Producción

Configure las siguientes variables en el panel de **Environment** de Render:

```env
# Configuración del Sistema
PROJECT_NAME="VotoSeguro API"
ENVIRONMENT=production
DEBUG=false
API_V1_STR=/api/v1
SECRET_KEY=98d6c7b04e82f1a94371b29a8f09d8e7c6b5a43210fe98dcba76543210fedcba
ACCESS_TOKEN_EXPIRE_MINUTES=480

# Base de Datos PostgreSQL
DATABASE_URL=postgresql+asyncpg://postgres:PASSWORD@host.supabase.co:5432/postgres

# Seguridad Criptográfica y Llave de Urna
MASTER_KEY=c39f82d1a4e7b0c95861427389abdef0123456789abcdef0123456789abcdef0
PAILLIER_KEY_SIZE=1024
SHAMIR_PRIME=115792089237316195423570985008687907853269984665640564039457584007913129639747

# Inteligencia Artificial en la Nube (Google Gemini 3.8)
GEMINI_API_KEY=AIzaSyD...TU_LLAVE_OFICIAL_AQUI
GEMINI_MODEL=gemini-3.8-flash
GEMINI_TIMEOUT_SECONDS=20.0

# Nodo Neuronal Local (Túnel ngrok)
LOCAL_AI_BASE_URL=https://tu-tunel.ngrok-free.dev
LOCAL_AI_MODEL=votoseguro-lfm3
LOCAL_AI_TIMEOUT_SECONDS=25.0
STRICT_NEURAL_MODE=false

# Rate Limiting y Protección DoS
RATE_LIMIT_ENABLED=true
RATE_LIMIT_DEFAULT=120/minute

# Notificaciones por Correo (SMTP Institucional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=votoseguro.uagrm@gmail.com
SMTP_PASSWORD=tu_contraseña_de_aplicacion
SMTP_FROM=notificaciones@votoseguro.uagrm.edu.bo
```

---

## 5. Despliegue del Frontend Web en Vercel

1. **Importación del Repositorio:**
   - Conecte su cuenta de GitHub a [vercel.com](https://vercel.com).
   - Seleccione el repositorio `votoseguro`.
2. **Configuración del Proyecto:**
   - **Framework Preset:** `Vite`.
   - **Root Directory:** `apps/web`.
   - **Build Command:** `pnpm build` (o `npm run build`).
   - **Output Directory:** `dist`.
3. **Variables de Entorno en Vercel:**
   ```env
   VITE_API_URL=https://votoseguro-api.onrender.com/api/v1
   ```
4. **Enrutamiento SPA (`vercel.json`):**
   Asegúrese de que `apps/web/vercel.json` contenga la regla de reescritura para rutas cliente:
   ```json
   {
     "rewrites": [
       { "source": "/(.*)", "destination": "/index.html" }
     ]
   }
   ```

---

## 6. Compilación y Despliegue de la App Móvil (Expo EAS)

La aplicación móvil está construida con React Native y Expo SDK 52.

1. **Instalación de EAS CLI:**
   ```bash
   npm install -g eas-cli
   eas login
   ```
2. **Configuración de Variables de Entorno en Móvil (`apps/mobile/.env`):**
   ```env
   EXPO_PUBLIC_API_URL=https://votoseguro-api.onrender.com/api/v1
   ```
3. **Compilación de Android APK para Pruebas e Instalación Directa:**
   ```bash
   cd apps/mobile
   eas build -p android --profile preview
   ```
4. **Compilación para Tiendas Oficiales (Google Play / App Store):**
   ```bash
   eas build -p android --profile production
   eas build -p ios --profile production
   ```

---

## 7. Puesta en Marcha del Nodo Neuronal Local con ngrok

1. **Instalación de LM Studio / Ollama:**
   - Descargue el modelo `Liquid-LFM-3b` y cree el alias `votoseguro-lfm3`.
   - Inicie el servidor local en el puerto `1234`.
2. **Instalación y Autenticación de ngrok:**
   ```powershell
   winget install ngrok
   ngrok config add-authtoken TU_AUTHTOKEN_DE_NGROK
   ```
3. **Ejecución Automática con `INICIAR_IA_LOCAL.bat`:**
   Ejecute el script en la raíz del proyecto para enlazar automáticamente el puerto `1234` con el backend en la nube.

---

## 8. Verificación de Salud Post-Despliegue

Una vez completado el despliegue, verifique que todos los subsistemas respondan correctamente:

1. **Health Check del Backend:**
   ```bash
   curl -X GET https://votoseguro-api.onrender.com/api/v1/health
   # Respuesta esperada: {"status":"healthy","database":"connected","version":"3.0.0"}
   ```
2. **Portal Público de Auditoría:**
   - Ingrese en el navegador a `https://votoseguro.vercel.app/audit-portal`.
   - Confirme la visualización de las elecciones públicas y la verificación matemática de comprobantes.
3. **Cabina de Votación:**
   - Ingrese a `https://votoseguro.vercel.app/vote` y compruebe el flujo de emisión con cifrado Paillier.

---

**Certificación de Despliegue:** Sistema homologado para producción y auditoría institucional abierta.
