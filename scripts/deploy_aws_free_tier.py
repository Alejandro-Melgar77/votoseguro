#!/usr/bin/env python3
"""
Orquestador de despliegue automatizado para VotoSeguro en AWS (Nivel Gratuito / Creditos FREE).
Despliega la infraestructura CloudFormation (EC2 t3.micro + S3), sincroniza el frontend y valida la salud del backend.
"""
import csv
import mimetypes
import os
import sys
import time
from pathlib import Path
import urllib.request
import json
import boto3
from botocore.exceptions import ClientError

STACK_NAME = "votoseguro-free-tier"
REGION = "us-east-1"
ROOT_DIR = Path(__file__).resolve().parent.parent

def load_aws_credentials():
    csv_path = ROOT_DIR / "IA-Codex_accessKeys.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"No se encontro el archivo de credenciales: {csv_path}")
    with csv_path.open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError("El archivo CSV no contiene credenciales.")
    row = rows[0]
    access_key = next((v for k, v in row.items() if "access key" in k.lower() and "secret" not in k.lower()), None)
    secret_key = next((v for k, v in row.items() if "secret" in k.lower()), None)
    if not access_key or not secret_key:
        raise ValueError("No se pudieron detectar las claves de acceso en el CSV.")
    return access_key.strip(), secret_key.strip()

def get_clients(access_key, secret_key):
    session = boto3.Session(
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=REGION
    )
    return {
        "cf": session.client("cloudformation"),
        "s3": session.client("s3"),
        "ec2": session.client("ec2")
    }

def deploy_stack(cf_client):
    template_path = ROOT_DIR / "infra" / "cloudformation" / "votoseguro-stack.yaml"
    template_body = template_path.read_text(encoding="utf-8")

    print(f"[*] Verificando estado del stack CloudFormation '{STACK_NAME}'...")
    stack_exists = False
    try:
        cf_client.describe_stacks(StackName=STACK_NAME)
        stack_exists = True
    except ClientError as e:
        if "does not exist" not in str(e):
            raise

    params = [
        {"ParameterKey": "InstanceType", "ParameterValue": "t3.micro"},
        {"ParameterKey": "GithubBranch", "ParameterValue": "JERS"},
    ]

    if not stack_exists:
        print(f"[*] Creando stack '{STACK_NAME}' en {REGION}...")
        cf_client.create_stack(
            StackName=STACK_NAME,
            TemplateBody=template_body,
            Parameters=params,
            Capabilities=["CAPABILITY_NAMED_IAM"],
            Tags=[
                {"Key": "Project", "Value": "VotoSeguro"},
                {"Key": "Environment", "Value": "FreeTier"},
                {"Key": "Branch", "Value": "JERS"}
            ]
        )
        print("[*] Esperando a que el stack complete su creacion (aprox 2-3 minutos)...")
        waiter = cf_client.get_waiter("stack_create_complete")
        waiter.wait(StackName=STACK_NAME, WaiterConfig={"Delay": 15, "MaxAttempts": 30})
        print("[+] Stack CloudFormation creado exitosamente.")
    else:
        print(f"[*] Stack '{STACK_NAME}' ya existe. Verificando actualizaciones...")
        try:
            cf_client.update_stack(
                StackName=STACK_NAME,
                TemplateBody=template_body,
                Parameters=params,
                Capabilities=["CAPABILITY_NAMED_IAM"]
            )
            print("[*] Esperando actualizacion del stack...")
            waiter = cf_client.get_waiter("stack_update_complete")
            waiter.wait(StackName=STACK_NAME, WaiterConfig={"Delay": 15, "MaxAttempts": 30})
            print("[+] Stack actualizado.")
        except ClientError as e:
            if "No updates are to be performed" in str(e):
                print("[*] No hay cambios en la plantilla de CloudFormation.")
            else:
                raise

    res = cf_client.describe_stacks(StackName=STACK_NAME)
    outputs = {o["OutputKey"]: o["OutputValue"] for o in res["Stacks"][0].get("Outputs", [])}
    return outputs

def upload_frontend(s3_client, bucket_name):
    dist_candidates = [
        ROOT_DIR / "votoseguro-main" / "apps" / "web" / "dist",
        ROOT_DIR / "votoseguro-JERS" / "apps" / "web" / "dist",
        ROOT_DIR / "apps" / "web" / "dist"
    ]
    dist_dir = next((d for d in dist_candidates if d.exists()), None)
    if not dist_dir:
        raise FileNotFoundError("No se encontro el directorio dist del frontend web compilado.")

    print(f"[*] Subiendo activos del frontend desde {dist_dir} al bucket S3 '{bucket_name}'...")
    uploaded_count = 0
    for root, _, files in os.walk(dist_dir):
        for file in files:
            local_path = Path(root) / file
            relative_key = local_path.relative_to(dist_dir).as_posix()

            mime_type, _ = mimetypes.guess_type(str(local_path))
            if not mime_type:
                if file.endswith(".wasm"):
                    mime_type = "application/wasm"
                elif file.endswith(".svg"):
                    mime_type = "image/svg+xml"
                else:
                    mime_type = "application/octet-stream"

            extra_args = {"ContentType": mime_type}
            if file == "index.html" or file == "_redirects":
                extra_args["CacheControl"] = "no-cache, no-store, must-revalidate"
            else:
                extra_args["CacheControl"] = "public, max-age=31536000, immutable"

            s3_client.upload_file(
                Filename=str(local_path),
                Bucket=bucket_name,
                Key=relative_key,
                ExtraArgs=extra_args
            )
            uploaded_count += 1

    print(f"[+] {uploaded_count} archivos subidos exitosamente a S3.")

def wait_for_backend_health(ec2_ip, timeout_seconds=300):
    url = f"http://{ec2_ip}/health"
    print(f"[*] Esperando inicializacion de Docker y FastAPI en {url} (tiempo limite: {timeout_seconds}s)...")
    start = time.time()
    while time.time() - start < timeout_seconds:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "HealthCheck/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    print(f"[+] Backend respondiendo exitosamente: {data}")
                    return True
        except Exception:
            pass
        time.sleep(10)
        elapsed = int(time.time() - start)
        print(f"    ... esperando arranque de contenedores ({elapsed}s transcurridos)")
    return False

def main():
    print("=" * 70)
    print(" DESPLIEGUE AUTOMATIZADO VOTOSEGURO - AWS FREE TIER (RAMA JERS)")
    print("=" * 70)

    access_key, secret_key = load_aws_credentials()
    clients = get_clients(access_key, secret_key)

    # 1. Desplegar Stack CloudFormation
    outputs = deploy_stack(clients["cf"])
    print("[*] Salidas de CloudFormation:")
    for k, v in outputs.items():
        print(f"    - {k}: {v}")

    bucket_name = outputs.get("WebBucketName")
    ec2_ip = outputs.get("EC2PublicIp")
    ec2_dns = outputs.get("EC2PublicDns")
    web_url_http = outputs.get("WebUrlHttp")
    web_url_ip = outputs.get("WebUrlIp")

    # 2. Subir Frontend Web a S3
    if bucket_name:
        upload_frontend(clients["s3"], bucket_name)

    # 3. Esperar y validar salud de la API en la instancia EC2
    if ec2_ip:
        healthy = wait_for_backend_health(ec2_ip, timeout_seconds=360)
        if not healthy:
            print("[!] Advertencia: La API aun esta completando su compilacion o arranque en segundo plano.")
            print("    Puedes revisar el estado en unos minutos o inspeccionar /var/log/user-data.log en la instancia.")

    print("\n" + "=" * 70)
    print(" DESPLIEGUE COMPLETADO EXITOSAMENTE EN AWS")
    print("=" * 70)
    print(f"URL de Acceso Web (DNS):      {web_url_http}")
    print(f"URL de Acceso Web (IP):       {web_url_ip}")
    print(f"Endpoint de Salud:            http://{ec2_ip}/health")
    print(f"Documentacion Swagger:        http://{ec2_ip}/docs")
    print(f"Administrador Inicial:        admin@votoseguro.org / AdminPlatform2026!")
    print(f"Demo Universidad:             admin@granestudio.edu.bo / GranEstudio2026!")
    print("=" * 70)

if __name__ == "__main__":
    main()
