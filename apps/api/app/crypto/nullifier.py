"""
Cálculo criptográfico de Nullifiers (HMAC-SHA256)
Garantiza el principio de 'Un voto por persona y cargo' sin vincular el voto con la identidad.
"""
import hashlib
import hmac
import uuid


def compute_nullifier(
    voter_id: uuid.UUID | str,
    constituency_id: uuid.UUID | str,
    secret: str | None = None,
) -> str:
    """
    Calcula el nullifier determinista y pseudoaleatorio para un votante y una circunscripción.
    nullifier = HMAC_SHA256(secret, voter_id || ":" || constituency_id)
    """
    if not secret:
        from app.core.config import settings
        secret = settings.NULLIFIER_SECRET

    message = f"{str(voter_id)}:{str(constituency_id)}".encode("utf-8")
    key = secret.encode("utf-8")
    return hmac.new(key, message, hashlib.sha256).hexdigest()
