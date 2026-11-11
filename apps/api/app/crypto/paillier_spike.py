"""
Spike Obligatorio de Cifrado Homomórfico Paillier (Sprint 2)
Implementa el motor de prueba de concepto PaillierTallySpikeEngine con suma de cifrados
agrupada por circunscripción y prefijos jerárquicos de segment_path.
Demuestra la equivalencia 100% matemática frente al conteo plano sin descifrar votos individuales.
"""
import time
from typing import Any
import phe.paillier as paillier


class PaillierTallySpikeEngine:
    def __init__(self, key_size: int = 1024):
        """
        Inicializa el motor generando un par de claves Paillier.
        1024 bits para ejecución veloz en demostración y tests; 2048 para producción.
        """
        t0 = time.perf_counter()
        self.public_key, self.private_key = paillier.generate_paillier_keypair(n_length=key_size)
        self.keygen_duration_ms = int((time.perf_counter() - t0) * 1000)
        self.key_size = key_size

    def encrypt_scalar(self, value: int) -> paillier.EncryptedNumber:
        """Cifra un entero escalar usando únicamente la clave pública."""
        return self.public_key.encrypt(value)

    def encode_and_encrypt_ballot(
        self,
        selected_index: int,
        num_options: int,
    ) -> list[paillier.EncryptedNumber]:
        """
        Codifica una selección electoral en un vector one-hot cifrado [E(0), ..., E(1), ..., E(0)].
        """
        vector = []
        for i in range(num_options):
            scalar = 1 if i == selected_index else 0
            vector.append(self.public_key.encrypt(scalar))
        return vector

    def aggregate_election_votes(
        self,
        ballots: list[dict[str, Any]],
        constituencies_options: dict[str, int],
    ) -> dict[str, dict[str, list[paillier.EncryptedNumber]]]:
        """
        Suma homomórficamente los vectores cifrados usando EXCLUSIVAMENTE la clave pública.
        Agrupa simultáneamente por circunscripción y por todos los prefijos de segment_path.

        ballots: lista de {
            "constituency_id": str,
            "segment_path": str,  # Ej: "/UAGRM/FICCT/INF/"
            "encrypted_vector": list[EncryptedNumber]
        }
        """
        # aggregated[constituency_id][prefix_path] = list of EncryptedNumber
        aggregated: dict[str, dict[str, list[paillier.EncryptedNumber]]] = {}

        for ballot in ballots:
            cid = ballot["constituency_id"]
            num_opts = constituencies_options[cid]
            path = ballot["segment_path"].strip()

            # Descomponer segment_path en prefijos acumulativos
            # Ej: "/UAGRM/FICCT/INF/" -> ["/UAGRM/", "/UAGRM/FICCT/", "/UAGRM/FICCT/INF/"]
            parts = [p for p in path.split("/") if p]
            prefixes = ["/"]
            curr = "/"
            for p in parts:
                curr += p + "/"
                prefixes.append(curr)

            if cid not in aggregated:
                aggregated[cid] = {}

            for prefix in prefixes:
                if prefix not in aggregated[cid]:
                    # Inicializar vector en ceros cifrados
                    aggregated[cid][prefix] = [self.public_key.encrypt(0) for _ in range(num_opts)]

                # Suma homomórfica vector a vector: E(a) + E(b) = E(a + b)
                for opt_idx in range(num_opts):
                    aggregated[cid][prefix][opt_idx] = (
                        aggregated[cid][prefix][opt_idx] + ballot["encrypted_vector"][opt_idx]
                    )

        return aggregated

    def decrypt_tallies(
        self,
        aggregated: dict[str, dict[str, list[paillier.EncryptedNumber]]],
    ) -> dict[str, dict[str, list[int]]]:
        """
        Descifra ÚNICAMENTE las sumas agregadas por celda con la clave privada.
        Jamás se descifra una papeleta individual.
        """
        decrypted_results: dict[str, dict[str, list[int]]] = {}

        for cid, paths_dict in aggregated.items():
            decrypted_results[cid] = {}
            for prefix, cipher_vector in paths_dict.items():
                decrypted_results[cid][prefix] = [
                    self.private_key.decrypt(cipher_elem) for cipher_elem in cipher_vector
                ]

        return decrypted_results

    def run_benchmark_simulation(
        self,
        constituencies_info: list[dict[str, Any]],
        num_simulated_votes: int = 15,
    ) -> dict[str, Any]:
        """
        Ejecuta una simulación completa de escrutinio homomórfico con verificación exacta.
        """
        t_start = time.perf_counter()

        options_map = {c["id"]: c["options_count"] for c in constituencies_info}

        # Generar votos simulados (texto plano y cifrado)
        simulated_ballots = []
        ground_truth_counts: dict[str, dict[str, list[int]]] = {}

        for c in constituencies_info:
            cid = c["id"]
            num_opts = c["options_count"]
            ground_truth_counts[cid] = {}

            sample_paths = c.get("sample_paths", ["/UAGRM/FICCT/INF/", "/UAGRM/FICCT/CIV/"])

            for v_idx in range(num_simulated_votes):
                chosen_option = v_idx % num_opts
                v_path = sample_paths[v_idx % len(sample_paths)]

                # Voto plano acumulativo
                parts = [p for p in v_path.split("/") if p]
                prefixes = ["/"]
                curr = "/"
                for p in parts:
                    curr += p + "/"
                    prefixes.append(curr)

                for prefix in prefixes:
                    if prefix not in ground_truth_counts[cid]:
                        ground_truth_counts[cid][prefix] = [0] * num_opts
                    ground_truth_counts[cid][prefix][chosen_option] += 1

                # Cifrado homomórfico del voto
                enc_vector = self.encode_and_encrypt_ballot(chosen_option, num_opts)
                simulated_ballots.append({
                    "constituency_id": cid,
                    "segment_path": v_path,
                    "encrypted_vector": enc_vector,
                })

        t_encrypted = time.perf_counter()

        # Suma homomórfica de todos los votos (clave pública únicamente)
        aggregated_ciphers = self.aggregate_election_votes(simulated_ballots, options_map)
        t_aggregated = time.perf_counter()

        # Descifrado exclusivo de las sumas finales
        decrypted_tallies = self.decrypt_tallies(aggregated_ciphers)
        t_decrypted = time.perf_counter()

        # Verificación de igualdad matemática 100% exacta
        exact_match = True
        verification_details = []

        for cid, paths in ground_truth_counts.items():
            for prefix, expected_vec in paths.items():
                actual_vec = decrypted_tallies[cid][prefix]
                matches = actual_vec == expected_vec
                if not matches:
                    exact_match = False
                verification_details.append({
                    "constituency_id": cid,
                    "segment_path": prefix,
                    "expected_plaintext_tally": expected_vec,
                    "decrypted_homomorphic_tally": actual_vec,
                    "is_exact_match": matches,
                })

        # Muestra de texto cifrado para inspección visual
        sample_ciphertext = None
        if simulated_ballots:
            sample_num = simulated_ballots[0]["encrypted_vector"][0]
            sample_ciphertext = str(sample_num.ciphertext())[:64] + "..."

        return {
            "key_size_bits": self.key_size,
            "keygen_duration_ms": self.keygen_duration_ms,
            "simulated_ballots_count": len(simulated_ballots),
            "encryption_duration_ms": int((t_encrypted - t_start) * 1000),
            "homomorphic_addition_duration_ms": int((t_aggregated - t_encrypted) * 1000),
            "final_decryption_duration_ms": int((t_decrypted - t_aggregated) * 1000),
            "total_benchmark_duration_ms": int((t_decrypted - t_start) * 1000),
            "sample_ciphertext_preview": sample_ciphertext,
            "mathematical_equivalence_verified": exact_match,
            "decrypted_tallies": decrypted_tallies,
            "verification_cells": verification_details,
        }
