"""
Pruebas Automatizadas del Spike de Cifrado Homomórfico Paillier (Sprint 2 Spike Obligatorio)
Verifica:
1. Generación de par de claves Paillier (pública y privada).
2. Encriptación homomórfica de papeletas como vectores one-hot.
3. Adición homomórfica en el dominio cifrado sin descifrar votos individuales.
4. Agrupación por circunscripción y por prefijo de ruta territorial (segment_path).
5. Descifrado agregado final y verificación del 100% de equivalencia con el escrutinio en texto claro.
6. Endpoint de benchmark criptográfico POST /api/v1/crypto/paillier-spike-benchmark.
"""
import pytest
from httpx import AsyncClient

from app.crypto.paillier_spike import PaillierTallySpikeEngine


def test_paillier_homomorphic_addition_and_equivalence():
    """
    Prueba unitaria de cálculo homomórfico directo con phe.
    Simula 15 votos en una circunscripción con 3 candidatos y verifica la suma homomórfica.
    """
    engine = PaillierTallySpikeEngine(key_size=512)

    # Votos: Candidato 0 (7 votos), Candidato 1 (5 votos), Candidato 2 (3 votos)
    votes_pattern = [0] * 7 + [1] * 5 + [2] * 3
    num_candidates = 3
    ballots = []

    for choice in votes_pattern:
        encrypted_vector = engine.encode_and_encrypt_ballot(
            selected_index=choice,
            num_options=num_candidates,
        )
        ballots.append({
            "constituency_id": "CONST-01",
            "segment_path": "/BOLIVIA/SANTA_CRUZ/",
            "encrypted_vector": encrypted_vector,
        })

    constituencies_options = {"CONST-01": num_candidates}

    # Suma homomórfica
    aggregated = engine.aggregate_election_votes(
        ballots=ballots,
        constituencies_options=constituencies_options,
    )

    # Descifrado agregado
    tally_result = engine.decrypt_tallies(aggregated)

    # Validar resultados descifrados agregados en el prefijo territorial
    assert tally_result["CONST-01"]["/BOLIVIA/SANTA_CRUZ/"] == [7, 5, 3]

    # Validar suma acumulativa en la raíz
    assert tally_result["CONST-01"]["/"] == [7, 5, 3]


@pytest.mark.asyncio
async def test_paillier_spike_benchmark_endpoint(client: AsyncClient, org1_setup):
    """
    Prueba de integración del endpoint oficial de benchmark de Paillier.
    """
    org, admin, admin_token = org1_setup
    auth_headers = {"Authorization": f"Bearer {admin_token}"}

    res_bench = await client.post(
        "/crypto/paillier-spike-benchmark?key_size=512&num_votes=15",
        headers=auth_headers,
    )
    assert res_bench.status_code == 200
    bench_data = res_bench.json()

    assert bench_data["key_size_bits"] == 512
    assert bench_data["simulated_ballots_count"] > 0
    assert bench_data["mathematical_equivalence_verified"] is True
    assert bench_data["encryption_duration_ms"] > 0
    assert bench_data["homomorphic_addition_duration_ms"] >= 0
    assert bench_data["final_decryption_duration_ms"] > 0
    assert len(bench_data["verification_cells"]) > 0
    assert bench_data["sample_ciphertext_preview"] is not None
