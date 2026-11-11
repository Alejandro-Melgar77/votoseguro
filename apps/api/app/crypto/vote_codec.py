"""
Abstracción de codificación y cifrado del voto (Regla Invariante #13)
Permite usar PlaintextVoteCodec en Sprint 1 y 2, y migrar a Paillier en Sprint 3 sin reescribir esquemas.
"""
import json
import uuid
from typing import Any, Protocol


class VoteCodec(Protocol):
    def encode(self, choice_type: str, candidate_id: uuid.UUID | None) -> str:
        """Codifica o cifra la selección del votante en una cadena de texto para BD."""
        ...

    def decode(self, payload: str) -> dict[str, Any]:
        """Decodifica o descifra la carga útil."""
        ...


class PlaintextVoteCodec:
    """
    Implementación en texto plano canónico JSON para Sprint 1 y Sprint 2.
    El anonimato en esta fase descansa en la separación física en PostgreSQL (tabla vote sin voter_id).
    """

    def encode(self, choice_type: str, candidate_id: uuid.UUID | None) -> str:
        data = {
            "choice_type": choice_type,
            "candidate_id": str(candidate_id) if candidate_id else None,
        }
        return json.dumps(data, sort_keys=True, separators=(",", ":"))

    def decode(self, payload: str) -> dict[str, Any]:
        return json.loads(payload)


class HomomorphicPaillierVoteCodec:
    """
    Contrato preparado para el Sprint 3: Cifrado Homomórfico de Paillier.
    Permite sumar vectores cifrados de votos sin descifrar votos individuales.
    """

    def __init__(self, public_key: Any = None, private_key: Any = None):
        self.public_key = public_key
        self.private_key = private_key

    def encode(self, choice_type: str, candidate_id: uuid.UUID | None) -> str:
        # En Sprint 3 utilizará python-paillier (phe)
        data = {
            "ciphertext_type": "PAILLIER_HOMOMORPHIC_V3",
            "choice_type": choice_type,
            "candidate_id": str(candidate_id) if candidate_id else None,
        }
        return json.dumps(data, sort_keys=True, separators=(",", ":"))

    def decode(self, payload: str) -> dict[str, Any]:
        return json.loads(payload)


# Instancia por defecto para Sprint 1 y 2
default_vote_codec: VoteCodec = PlaintextVoteCodec()
