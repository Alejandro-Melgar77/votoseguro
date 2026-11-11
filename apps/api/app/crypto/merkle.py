"""
Motor de Árbol de Merkle Criptográfico para Congelamiento del Padrón Electoral (S2-07)
Implementa construcción canónica, cálculo de raíz y generación/verificación de pruebas de inclusión.
"""
from typing import Any
from app.crypto.hashing import canonical_json, sha256_hex


def compute_voter_leaf_hash(
    election_id: str,
    document_id: str,
    group_code: str,
    node_path: str,
    status: str = "ACTIVE",
) -> str:
    """
    Calcula el hash canónico SHA-256 de una hoja del padrón electoral con prefijo de dominio 0x00.
    """
    leaf_payload = {
        "document_id": str(document_id).strip(),
        "election_id": str(election_id),
        "group_code": str(group_code or "").strip(),
        "node_path": str(node_path or "").strip(),
        "status": status,
    }
    raw_bytes = b"\x00" + canonical_json(leaf_payload)
    return sha256_hex(raw_bytes)


class MerkleTree:
    def __init__(self, leaves: list[str], election_id: str):
        self.election_id = str(election_id)
        self.leaves = list(leaves)
        self.levels: list[list[str]] = []
        self.root: str = self._build_tree()

    def _build_tree(self) -> str:
        if not self.leaves:
            empty_bytes = b"VOTOSEGURO:EMPTY_MERKLE_TREE:" + self.election_id.encode("utf-8")
            empty_root = sha256_hex(empty_bytes)
            self.levels = [[empty_root]]
            return empty_root

        current_level = list(self.leaves)
        self.levels = [current_level]

        while len(current_level) > 1:
            next_level: list[str] = []
            # Si el nivel tiene cantidad impar de nodos, duplicar el último
            if len(current_level) % 2 != 0:
                current_level.append(current_level[-1])

            for i in range(0, len(current_level), 2):
                left_hash = current_level[i]
                right_hash = current_level[i + 1]
                parent_bytes = b"\x01" + bytes.fromhex(left_hash) + bytes.fromhex(right_hash)
                parent_hash = sha256_hex(parent_bytes)
                next_level.append(parent_hash)

            current_level = next_level
            self.levels.append(current_level)

        return self.levels[-1][0]

    def get_inclusion_proof(self, leaf_index: int) -> list[dict[str, str]]:
        """
        Genera el camino de prueba de inclusión para una hoja sin revelar el resto del padrón.
        Cada paso contiene { 'position': 'left' | 'right', 'sibling_hash': '<sha256>' }
        """
        if leaf_index < 0 or leaf_index >= len(self.leaves):
            raise IndexError("Índice de hoja fuera de los límites del padrón electoral.")

        proof: list[dict[str, str]] = []
        idx = leaf_index

        for level_idx in range(len(self.levels) - 1):
            level = list(self.levels[level_idx])
            # Replicar duplicación si era impar
            if len(level) % 2 != 0:
                level.append(level[-1])

            if idx % 2 == 0:
                sibling_idx = idx + 1
                position = "right"
            else:
                sibling_idx = idx - 1
                position = "left"

            proof.append({
                "position": position,
                "sibling_hash": level[sibling_idx],
            })
            idx = idx // 2

        return proof


def verify_merkle_inclusion_proof(
    leaf_hash: str,
    merkle_root: str,
    proof: list[dict[str, str]],
) -> bool:
    """
    Verifica matemáticamente una prueba de inclusión recalculando la raíz paso a paso.
    """
    current_hash = leaf_hash.strip().lower()

    for step in proof:
        position = step.get("position")
        sibling_hex = step.get("sibling_hash", "").strip().lower()
        if not sibling_hex:
            return False

        try:
            curr_bytes = bytes.fromhex(current_hash)
            sibling_bytes = bytes.fromhex(sibling_hex)
        except ValueError:
            return False

        if position == "left":
            parent_bytes = b"\x01" + sibling_bytes + curr_bytes
        elif position == "right":
            parent_bytes = b"\x01" + curr_bytes + sibling_bytes
        else:
            return False

        current_hash = sha256_hex(parent_bytes)

    return current_hash == merkle_root.strip().lower()
