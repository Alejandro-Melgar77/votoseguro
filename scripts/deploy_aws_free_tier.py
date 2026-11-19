#!/usr/bin/env python3
"""
Despliegue de VotoSeguro en AWS (capa gratuita, un único EC2) desde la rama JERS.

Pasos:
  1. Crea o actualiza el stack CloudFormation (EC2 t3.micro + bucket S3 del frontend).
  2. Compila el frontend web (VITE_API_BASE_URL=/api/v1) y lo sube al bucket.
  3. Ejecuta infra/aws/server/update.sh en el EC2 vía SSM: git pull de JERS,
     reconstrucción de la API, sincronización del frontend y HTTPS (Let's Encrypt).

Credenciales: cadena estándar de AWS (variables AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY,
perfil o rol). Nunca se guardan claves dentro del repositorio.

Uso:
    python scripts/deploy_aws_free_tier.py            # todo
    python scripts/deploy_aws_free_tier.py --skip-stack
"""
import argparse
import json
import mimetypes
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

STACK_NAME = "votoseguro-free-tier"
REGION = os.environ.get("AWS_REGION", "us-east-1")
ROOT_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT_DIR / "apps" / "web"


def deploy_stack(cf_client) -> dict[str, str]:
    template_body = (ROOT_DIR / "infra" / "cloudformation" / "votoseguro-stack.yaml").read_text(encoding="utf-8")
    params = [
        {"ParameterKey": "InstanceType", "ParameterValue": "t3.micro"},
        {"ParameterKey": "GithubBranch", "ParameterValue": "JERS"},
    ]
    try:
        cf_client.describe_stacks(StackName=STACK_NAME)
        exists = True
    except ClientError as e:
        if "does not exist" not in str(e):
            raise
        exists = False

    if not exists:
        print(f"[*] Creando stack '{STACK_NAME}' en {REGION}...")
        cf_client.create_stack(
            StackName=STACK_NAME,
            TemplateBody=template_body,
            Parameters=params,
            Capabilities=["CAPABILITY_NAMED_IAM"],
            Tags=[{"Key": "Project", "Value": "VotoSeguro"}, {"Key": "Branch", "Value": "JERS"}],
        )
        cf_client.get_waiter("stack_create_complete").wait(
            StackName=STACK_NAME, WaiterConfig={"Delay": 15, "MaxAttempts": 40}
        )
    else:
        print(f"[*] Stack '{STACK_NAME}' existente; la instancia se actualiza vía SSM (sin reemplazo).")

    res = cf_client.describe_stacks(StackName=STACK_NAME)
    return {o["OutputKey"]: o["OutputValue"] for o in res["Stacks"][0].get("Outputs", [])}


def build_frontend() -> Path:
    print("[*] Compilando frontend web...")
    env = {**os.environ, "VITE_API_BASE_URL": "/api/v1"}
    npm = "npm.cmd" if os.name == "nt" else "npm"
    subprocess.run([npm, "run", "build"], cwd=WEB_DIR, env=env, check=True)
    return WEB_DIR / "dist"


def upload_frontend(s3_client, bucket_name: str, dist_dir: Path) -> None:
    print(f"[*] Subiendo {dist_dir} a s3://{bucket_name} ...")
    count = 0
    for local_path in dist_dir.rglob("*"):
        if not local_path.is_file():
            continue
        key = local_path.relative_to(dist_dir).as_posix()
        mime_type = mimetypes.guess_type(local_path.name)[0]
        if local_path.suffix == ".wasm":
            mime_type = "application/wasm"
        extra = {"ContentType": mime_type or "application/octet-stream"}
        if key.startswith("assets/"):
            extra["CacheControl"] = "public, max-age=31536000, immutable"
        else:
            extra["CacheControl"] = "no-cache"
        s3_client.upload_file(str(local_path), bucket_name, key, ExtraArgs=extra)
        count += 1
    print(f"[+] {count} archivos subidos.")


def run_server_update(ssm_client, instance_id: str) -> bool:
    print(f"[*] Ejecutando update.sh en {instance_id} vía SSM...")
    command = (
        "cd /opt/votoseguro/app && git fetch --quiet origin JERS && git reset --quiet --hard origin/JERS && "
        "bash infra/aws/server/update.sh"
    )
    cid = ssm_client.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={"commands": [command], "executionTimeout": ["1800"]},
    )["Command"]["CommandId"]
    while True:
        time.sleep(5)
        try:
            out = ssm_client.get_command_invocation(CommandId=cid, InstanceId=instance_id)
        except ssm_client.exceptions.InvocationDoesNotExist:
            continue
        if out["Status"] not in ("Pending", "InProgress", "Delayed"):
            break
    print(out["StandardOutputContent"][-3000:])
    if out["Status"] != "Success":
        print(out["StandardErrorContent"][-3000:], file=sys.stderr)
    return out["Status"] == "Success"


def check_health(url: str) -> None:
    try:
        with urllib.request.urlopen(f"{url}/health", timeout=10) as resp:
            print(f"[+] {url}/health -> {json.loads(resp.read())}")
    except Exception as err:  # noqa: BLE001
        print(f"[!] No se pudo verificar {url}/health: {err}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-stack", action="store_true")
    parser.add_argument("--skip-build", action="store_true")
    args = parser.parse_args()

    session = boto3.Session(region_name=REGION)
    cf, s3, ssm, ec2 = (session.client(n) for n in ("cloudformation", "s3", "ssm", "ec2"))

    if args.skip_stack:
        res = cf.describe_stacks(StackName=STACK_NAME)
        outputs = {o["OutputKey"]: o["OutputValue"] for o in res["Stacks"][0].get("Outputs", [])}
    else:
        outputs = deploy_stack(cf)

    bucket = outputs["WebBucketName"]
    ip = outputs["EC2PublicIp"]
    instance_id = ec2.describe_instances(Filters=[{"Name": "ip-address", "Values": [ip]}])[
        "Reservations"][0]["Instances"][0]["InstanceId"]

    dist = WEB_DIR / "dist" if args.skip_build else build_frontend()
    upload_frontend(s3, bucket, dist)

    ok = run_server_update(ssm, instance_id)
    url = f"https://{ip.replace('.', '-')}.sslip.io"
    check_health(url)
    print("=" * 70)
    print(f" VotoSeguro: {url}" if ok else " La actualización del servidor falló; revise la salida anterior.")
    print("=" * 70)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
