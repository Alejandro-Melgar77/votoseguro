# Guía de Despliegue en AWS (Nivel Gratuito / Créditos Plan FREE)

La plataforma **VotoSeguro** se encuentra completamente desplegada y en operación activa en **AWS (Región us-east-1)**, extrayendo el código directamente desde la rama **`JERS`** del repositorio [https://github.com/Alejandro-Melgar77/votoseguro](https://github.com/Alejandro-Melgar77/votoseguro).

---

## 1. URLs de Acceso y Estado de Servicios

| Recurso / Servicio | URL / Dirección | Descripción |
| :--- | :--- | :--- |
| **Portal Web (DNS Oficial)** | [http://ec2-32-197-219-229.compute-1.amazonaws.com](http://ec2-32-197-219-229.compute-1.amazonaws.com) | Frontend React con OCR y votación privada |
| **Portal Web (IP Directa)** | [http://32.197.219.229](http://32.197.219.229) | Acceso directo sin resolución DNS externa |
| **API Health Check** | [http://32.197.219.229/health](http://32.197.219.229/health) | Comprobación de salud en vivo de API y PostgreSQL |
| **Documentación Swagger** | [http://32.197.219.229/docs](http://32.197.219.229/docs) | Catálogo interactivo OpenAPI de todos los endpoints |
| **OpenAPI Spec** | [http://32.197.219.229/openapi.json](http://32.197.219.229/openapi.json) | Especificación JSON de rutas |

---

## 2. Credenciales de Acceso Iniciales Sembradas

### Superadministrador de Plataforma
- **Email:** `admin@votoseguro.org`
- **Contraseña:** `AdminPlatform2026!`
- **Rol:** `PLATFORM_ADMIN` (gestión de instituciones, aprobación de elecciones)

### Demostración Universitaria (Universidad EL GRAN ESTUDIO)
- **Admin General:** `admin@granestudio.edu.bo` / `GranEstudio2026!` (Dr. Fernando Torrico)
- **Delegado de Segmento:** `delegado.docentes@granestudio.edu.bo` / `Docentes2026!`
- **Votante Ejemplo:** Cédula y acceso provisto en el padrón electoral

### Demostración Nacional (Elecciones Nacionales Ecuador)
- **Admin Electoral:** `admin@cne.gob.ec` / `Ecuador2026!`

---

## 3. Arquitectura Implementada (Optimización Cero Costos)

```
[ Usuario / Navegador Web ]
          │
          │ HTTP Port 80 (o HTTPS Port 443 SSL Autofirmado)
          ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Amazon EC2 (t3.micro - 1 vCPU, 1 GB RAM + 2 GB Swap - us-east-1a)      │
│ ────────────────────────────────────────────────────────────────────── │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │ Nginx Reverse Proxy (Puerto 80 / 443)                          │   │
│   │  ├─ /              ──> /var/www/votoseguro/web (Frontend React)│   │
│   │  ├─ /api/v1/       ──> 127.0.0.1:8000 (Proxy a FastAPI)       │   │
│   │  ├─ /docs          ──> 127.0.0.1:8000/docs                     │   │
│   │  └─ /health        ──> 127.0.0.1:8000/api/v1/health            │   │
│   └────────────────────────────────────────────────────────────────┘   │
│                                │                                       │
│                ┌───────────────┴───────────────┐                       │
│                ▼                               ▼                       │
│   ┌───────────────────────────┐   ┌───────────────────────────────┐    │
│   │ Contenedor Docker: api    │   │ Contenedor Docker: postgres   │    │
│   │ (FastAPI + APScheduler)   │──>│ (PostgreSQL 16 Alpine)        │    │
│   │ Migraciones Alembic 1-8   │   │ Volumen EBS persistente pgdata│    │
│   └───────────────────────────┘   └───────────────────────────────┘    │
└────────────────────────────────────────────────────────────────────────┘
```

### Por qué esta arquitectura garantiza tarifa $0 / preservación de créditos:
1. **EC2 t3.micro:** Forma parte de las **750 horas mensuales gratuitas** de la capa gratuita de AWS.
2. **Almacenamiento EBS gp3 (20 GB):** La capa gratuita incluye hasta 30 GB al mes sin costo.
3. **Memoria Swap (2 GB):** Permite ejecutar PostgreSQL 16 y FastAPI con total estabilidad sin necesidad de pagar por una instancia grande.
4. **Descarte de NAT Gateway y ALB:** Evita los ~$85 USD mensuales que habrían agotado los créditos de la cuenta en pocas semanas.
5. **Mismo Origen (Same-Origin):** Frontend y Backend comparten la misma IP y puerto 80, eliminando fallos de CORS y la necesidad de comprar dominios.

---

## 4. Mantenimiento y Actualización desde GitHub (Rama `JERS`)

El servidor está configurado para actualizarse directamente ante nuevos commits en la rama `JERS`.

### Opción A: Desde la Consola de AWS (AWS Systems Manager - Sin claves SSH)
1. Ingrese a la consola de AWS -> **EC2** -> Seleccione la instancia `votoseguro-free-tier-server`.
2. Haga clic en **Connect** -> **Session Manager** -> **Connect**.
3. Ejecute el comando de actualización:
   ```bash
   sudo /opt/votoseguro/update.sh
   ```
   Este script descarga los últimos cambios de `origin/JERS`, reconstruye los contenedores si es necesario y reinicia el servicio sin interrupciones.

### Opción B: Inspección de Logs
Para ver los registros en vivo del backend:
```bash
docker logs -f votoseguro-api
```
Para ver los registros de la base de datos:
```bash
docker logs -f votoseguro-postgres
```

---

## 5. Limpieza / Apagado de Recursos (Cuando Finalice el Proyecto)

Para destruir todos los recursos y garantizar que nunca se genere ningún cobro en el futuro:

```powershell
py -3.13 -c "
import csv, boto3
with open('IA-Codex_accessKeys.csv', encoding='utf-8-sig') as f:
    row = list(csv.DictReader(f))[0]
ak = [v for k,v in row.items() if 'access key' in k.lower() and 'secret' not in k.lower()][0].strip()
sk = [v for k,v in row.items() if 'secret' in k.lower()][0].strip()
cf = boto3.client('cloudformation', aws_access_key_id=ak, aws_secret_access_key=sk, region_name='us-east-1')
cf.delete_stack(StackName='votoseguro-free-tier')
print('Eliminación del stack completada. Todos los recursos fueron destruidos.')
"
```
