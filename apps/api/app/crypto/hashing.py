"""
Utilidades criptográficas para hashes canónicos deterministas (SHA-256)
"""
import hashlib
import json
from typing import Any


def canonical_json(data: Any) -> bytes:
    """Genera bytes de JSON canónico (ordenado por claves, sin espacios)."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(data: bytes | str) -> str:
    """Calcula el hash SHA-256 en formato hexadecimal."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def compute_receipt_hash(nullifiers: list[str], election_id: str, nonce: str) -> str:
    """Calcula el receipt_hash del comprobante para una papeleta emitida."""
    payload = {
        "election_id": str(election_id),
        "nonce": str(nonce),
        "nullifiers": sorted(nullifiers),
    }
    return sha256_hex(canonical_json(payload))
