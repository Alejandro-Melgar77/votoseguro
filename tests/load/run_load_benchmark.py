"""
VotoSeguro v3.0.0 — Python Asynchronous Concurrency & Benchmark Runner (S3-04)
Permite ejecutar y verificar el benchmark de concurrencia y latencia p(95) < 2000ms
directamente desde Python / CI / local sin requerir instalación previa del binario k6.
"""
import argparse
import asyncio
import json
import math
import sys
import time
from pathlib import Path
from typing import Any

# Asegurar importación de app desde apps/api
CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_DIR.parent / "votoseguro" if (CURRENT_DIR.parent / "votoseguro").exists() else CURRENT_DIR.parent
API_DIR = REPO_ROOT / "apps" / "api"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

import httpx


async def run_single_voter_flow(
    client: httpx.AsyncClient,
    base_url: str,
    voter: dict[str, Any],
    stats: dict[str, Any],
    semaphore: asyncio.Semaphore,
):
    async with semaphore:
        t_start = time.perf_counter()
        doc_id = voter["document_id"]
        cred_code = voter["credential_code"]

        try:
            # 1. Login
            t0 = time.perf_counter()
            login_res = await client.post(
                f"{base_url}/voter/login",
                json={"document_id": doc_id, "credential_code": cred_code},
                timeout=10.0,
            )
            login_ms = (time.perf_counter() - t0) * 1000.0
            if login_res.status_code != 200:
                stats["failed"] += 1
                stats["errors"].append(f"Login failed {login_res.status_code}: {login_res.text[:100]}")
                return

            token = login_res.json()["access_token"]
            auth_headers = {"Authorization": f"Bearer {token}"}

            # 2. Get Ballot
            t1 = time.perf_counter()
            ballot_res = await client.get(
                f"{base_url}/ballot",
                headers=auth_headers,
                timeout=10.0,
            )
            ballot_ms = (time.perf_counter() - t1) * 1000.0
            if ballot_res.status_code != 200:
                stats["failed"] += 1
                stats["errors"].append(f"Ballot failed {ballot_res.status_code}")
                return

            # Construir selección de voto
            contest_id = voter.get("contest_id")
            constituency_id = voter.get("constituency_id")
            choice_type = voter.get("choice_type", "CANDIDATE")
            cand_id = voter.get("candidate_id")

            # 3. Cast Ballot (Ruta Crítica Paillier)
            t2 = time.perf_counter()
            cast_res = await client.post(
                f"{base_url}/ballot/cast",
                headers=auth_headers,
                json={
                    "selections": [
                        {
                            "contest_id": contest_id,
                            "constituency_id": constituency_id,
                            "choice_type": choice_type,
                            "candidate_id": cand_id,
                        }
                    ]
                },
                timeout=15.0,
            )
            cast_ms = (time.perf_counter() - t2) * 1000.0
            stats["cast_latencies"].append(cast_ms)

            if cast_res.status_code != 201:
                stats["failed"] += 1
                stats["errors"].append(f"Cast failed {cast_res.status_code}: {cast_res.text[:100]}")
                return

            receipt_hash = cast_res.json()["receipt_hash"]

            # 4. Verify Receipt
            t3 = time.perf_counter()
            verify_res = await client.get(
                f"{base_url}/receipts/{receipt_hash}",
                timeout=10.0,
            )
            verify_ms = (time.perf_counter() - t3) * 1000.0

            total_ms = (time.perf_counter() - t_start) * 1000.0
            stats["total_latencies"].append(total_ms)
            stats["successful"] += 1

        except Exception as exc:
            stats["failed"] += 1
            stats["errors"].append(str(exc))


async def main_benchmark(
    base_url: str = "http://localhost:8000/api/v1",
    concurrency: int = 100,
    max_voters: int = 500,
):
    print("=" * 80)
    print("VOTOSEGURO v3.0.0 — PYTHON ASYNC CONCURRENCY BENCHMARK RUNNER")
    print(f"Target URL: {base_url}")
    print(f"Concurrencia Máxima (VUs): {concurrency}")
    print(f"Votantes a simular: {max_voters}")
    print("=" * 80)

    # Cargar credenciales
    cred_file = CURRENT_DIR / "voters_credentials.json"
    if not cred_file.exists():
        cred_file = REPO_ROOT / "tests" / "load" / "voters_credentials.json"

    if not cred_file.exists():
        print(f"[-] Archivo de credenciales no encontrado en: {cred_file}")
        print("    Ejecute primero: python prepare_load_test_election.py")
        sys.exit(1)

    with open(cred_file, "r", encoding="utf-8") as f:
        voters = json.load(f)

    if len(voters) > max_voters:
        voters = voters[:max_voters]

    stats = {
        "successful": 0,
        "failed": 0,
        "cast_latencies": [],
        "total_latencies": [],
        "errors": [],
    }

    semaphore = asyncio.Semaphore(concurrency)
    limits = httpx.Limits(max_connections=concurrency + 50, max_keepalive_connections=50)

    t_global_start = time.perf_counter()
    async with httpx.AsyncClient(limits=limits) as client:
        tasks = [
            run_single_voter_flow(client, base_url, voter, stats, semaphore)
            for voter in voters
        ]
        await asyncio.gather(*tasks)

    t_global_sec = time.perf_counter() - t_global_start

    # Calcular estadísticas
    total_reqs = stats["successful"] + stats["failed"]
    cast_lats = sorted(stats["cast_latencies"]) if stats["cast_latencies"] else [0.0]

    p50 = cast_lats[int(len(cast_lats) * 0.50)]
    p90 = cast_lats[int(len(cast_lats) * 0.90)]
    p95 = cast_lats[int(len(cast_lats) * 0.95)]
    p99 = cast_lats[int(len(cast_lats) * 0.99)]
    avg_cast = sum(cast_lats) / len(cast_lats)

    error_rate = (stats["failed"] / total_reqs * 100.0) if total_reqs > 0 else 0.0
    throughput = stats["successful"] / t_global_sec if t_global_sec > 0 else 0.0

    print("\n" + "=" * 80)
    print("INFORME DE RENDIMIENTO Y LATENCIA (BENCHMARK RESULTS)")
    print("=" * 80)
    print(f"Duración total del test:       {t_global_sec:.2f} s")
    print(f"Votos exitosos:                {stats['successful']} / {total_reqs} ({100.0 - error_rate:.2f}%)")
    print(f"Votos fallidos:                {stats['failed']} ({error_rate:.2f}%)")
    print(f"Rendimiento efectivo:          {throughput:.2f} votos emitidos / segundo")
    print("-" * 80)
    print("LATENCIA DE EMISIÓN DE PAPELETA ATÓMICA CON CIFRADO PAILLIER (/ballot/cast):")
    print(f"  Promedio:                    {avg_cast:.2f} ms")
    print(f"  Mediana (p50):               {p50:.2f} ms")
    print(f"  Percentil 90 (p90):          {p90:.2f} ms")
    print(f"  Percentil 95 (p95):          {p95:.2f} ms   <--- [UMBRAL EXIGIDO: < 2000 ms]")
    print(f"  Percentil 99 (p99):          {p99:.2f} ms")
    print("-" * 80)

    # Evaluación de Umbrales de Calidad
    passed_p95 = p95 < 2000.0
    passed_err = error_rate < 1.0

    print(f"Cumplimiento RNF Latencia (p95 < 2000ms): {'[PASSED] APROBADO' if passed_p95 else '[FAILED] RECHAZADO'}")
    print(f"Cumplimiento RNF Errores  (rate < 1.0%):  {'[PASSED] APROBADO' if passed_err else '[FAILED] RECHAZADO'}")

    if stats["errors"]:
        print("\nMuestras de errores detectados (primeros 5):")
        for err in stats["errors"][:5]:
            print(f"  - {err}")

    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Runner asíncrono de estrés y concurrencia.")
    parser.add_argument("--url", type=str, default="http://localhost:8000/api/v1", help="URL base de la API")
    parser.add_argument("--concurrency", type=int, default=50, help="Concurrencia máxima simultánea")
    parser.add_argument("--voters", type=int, default=200, help="Número de votantes a ejecutar")
    args = parser.parse_args()

    asyncio.run(
        main_benchmark(
            base_url=args.url,
            concurrency=args.concurrency,
            max_voters=args.voters,
        )
    )
