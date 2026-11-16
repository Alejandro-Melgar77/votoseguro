"""
S3-01: Cifrado Homomórfico Paillier en Producción y Escrutinio por Circunscripción y Segmento
Valida Invariantes #9 (Desvinculación), #12 (k-Anonimato) e #13 (VoteCodec seguro).
"""
import pytest
from tests.test_paillier_production_and_shamir import (
    test_paillier_vector_encryption_and_homomorphic_addition_exact_match,
    test_homomorphic_tally_engine_k_anonymity_suppression,
)

__all__ = [
    "test_paillier_vector_encryption_and_homomorphic_addition_exact_match",
    "test_homomorphic_tally_engine_k_anonymity_suppression",
]
