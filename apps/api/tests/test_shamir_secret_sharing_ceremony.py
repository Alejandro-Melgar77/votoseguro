"""
S3-02: Esquema de Secreto Compartido de Shamir (k de n) y Ceremonia de la Corte Electoral
Valida reconstrucción con k fragmentos, fallo estricto con k-1 fragmentos y compromisos SHA-256.
"""
import pytest
from tests.test_paillier_production_and_shamir import (
    test_shamir_threshold_reconstruction_and_sub_threshold_failure,
    test_e2e_ceremony_setup_voting_closed_and_shamir_unlock,
)

__all__ = [
    "test_shamir_threshold_reconstruction_and_sub_threshold_failure",
    "test_e2e_ceremony_setup_voting_closed_and_shamir_unlock",
]
