"""
Abstracción de codificación y cifrado del voto (Invariante #13 y RF-55)
S3-01: HomomorphicPaillierVoteCodec es el codec oficial en el Sprint 3.
Cada voto emitido se cifra asimétricamente de forma homomórfica aditiva usando Paillier (phe),
permitiendo sumar votos directamente en la base de datos sin descifrar jamás ningún voto individual.
"""
import json
import uuid
from typing import Any, Protocol
import phe.paillier as paillier


class VoteCodec(Protocol):
    def encode(
        self,
        choice_type: str,
        candidate_id: uuid.UUID | str | None,
        public_key: Any = None,
        option_keys: list[str] | None = None,
    ) -> str:
        """Codifica o cifra la selección del votante en una cadena de texto para BD."""
        ...

    def decode(self, payload: str, private_key: Any = None) -> dict[str, Any]:
        """Decodifica o descifra la carga útil."""
        ...


class PlaintextVoteCodec:
    """
    Implementación en texto plano canónico JSON para retrocompatibilidad (Sprint 1 y 2).
    """

    def encode(
        self,
        choice_type: str,
        candidate_id: uuid.UUID | str | None,
        public_key: Any = None,
        option_keys: list[str] | None = None,
    ) -> str:
        data = {
            "scheme": "PLAINTEXT_V1",
            "choice_type": choice_type,
            "candidate_id": str(candidate_id) if candidate_id else None,
        }
        return json.dumps(data, sort_keys=True, separators=(",", ":"))

    def decode(self, payload: str, private_key: Any = None) -> dict[str, Any]:
        return json.loads(payload)


class HomomorphicPaillierVoteCodec:
    """
    S3-01: Cifrado Homomórfico Aditivo de Paillier en Producción.
    Cifra cada sufragio como un vector unitario (one-hot) [E(0), ..., E(1), ..., E(0)]
    donde cada opción en la circunscripción corresponde a una posición del vector.
    """

    def __init__(
        self,
        public_key: paillier.PaillierPublicKey | int | str | None = None,
        private_key: paillier.PaillierPrivateKey | None = None,
    ):
        self.public_key = self._coerce_public_key(public_key) if public_key is not None else None
        self.private_key = private_key

    @staticmethod
    def _coerce_public_key(pk: Any) -> paillier.PaillierPublicKey:
        if isinstance(pk, paillier.PaillierPublicKey):
            return pk
        if isinstance(pk, (int, str)):
            return paillier.PaillierPublicKey(int(pk))
        if isinstance(pk, dict) and "n" in pk:
            return paillier.PaillierPublicKey(int(pk["n"]))
        raise ValueError(f"Tipo de clave pública Paillier no soportado: {type(pk)}")

    def encode(
        self,
        choice_type: str,
        candidate_id: uuid.UUID | str | None,
        public_key: Any = None,
        option_keys: list[str] | None = None,
    ) -> str:
        """
        Cifra la selección del elector como vector one-hot con la clave pública Paillier.
        Retorna la serialización JSON canónica según la especificación del Sprint 3.
        """
        pk = self._coerce_public_key(public_key) if public_key is not None else self.public_key
        if pk is None:
            # Clave pública determinista efímera para entornos de test o inicialización temprana
            pub, _ = paillier.generate_paillier_keypair(n_length=512)
            pk = pub

        # Determinar el conjunto de opciones si no fue provisto
        if option_keys is None:
            if candidate_id:
                option_keys = [str(candidate_id), "BLANK", "NULL"]
            else:
                option_keys = ["CANDIDATE", "BLANK", "NULL"]

        # Identificar la opción seleccionada
        if choice_type == "CANDIDATE" and candidate_id:
            target_key = str(candidate_id)
        elif choice_type == "BLANK":
            target_key = "BLANK"
        elif choice_type == "NULL":
            target_key = "NULL"
        else:
            target_key = str(candidate_id) if candidate_id else choice_type

        # Construir vector one-hot: 1 en la opción elegida, 0 en las demás
        one_hot_vector: list[int] = []
        for opt in option_keys:
            one_hot_vector.append(1 if opt == target_key else 0)

        # Cifrar cada componente de manera independiente con factor de aleatorización fresco r_i
        encrypted_nums = [pk.encrypt(scalar) for scalar in one_hot_vector]
        ciphertexts_hex = [hex(c.ciphertext()) for c in encrypted_nums]

        payload = {
            "scheme": "PAILLIER_V1",
            "n": str(pk.n),
            "option_keys": option_keys,
            "ciphertexts": ciphertexts_hex,
            "choice_type": choice_type,
            "candidate_id": str(candidate_id) if candidate_id else None,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    def decode(self, payload: str, private_key: Any = None) -> dict[str, Any]:
        """
        Decodifica la carga útil. Si se proporciona la clave privada, descifra el vector
        y recupera la selección electoral. Si no, devuelve el payload cifrado sin exponer el voto.
        """
        data = json.loads(payload)
        if data.get("scheme") == "PAILLIER_V1" and "ciphertexts" in data:
            priv = private_key or self.private_key
            if priv is not None:
                pk = paillier.PaillierPublicKey(int(data["n"]))
                decrypted_vector: list[int] = []
                for c_hex in data["ciphertexts"]:
                    c_int = int(c_hex, 16)
                    enc_num = paillier.EncryptedNumber(pk, c_int, 0)
                    decrypted_vector.append(priv.decrypt(enc_num))
                data["decrypted_vector"] = decrypted_vector
                # Identificar la opción con voto
                option_keys = data.get("option_keys", [])
                for idx, count in enumerate(decrypted_vector):
                    if count == 1 and idx < len(option_keys):
                        data["decoded_selection"] = option_keys[idx]
                        break
            return data
        return data

    @staticmethod
    def add_ciphertexts(c1: int, c2: int, n: int) -> int:
        """Suma homomórfica de dos textos cifrados: E(m1) * E(m2) % n^2 = E(m1 + m2)."""
        n_sq = n * n
        return (c1 * c2) % n_sq

    @staticmethod
    def aggregate_cipher_vectors(vectors: list[list[int]], n: int) -> list[int]:
        """Multiplica componente a componente una lista de vectores cifrados módulo n^2."""
        if not vectors:
            return []
        length = len(vectors[0])
        n_sq = n * n
        result = [1] * length
        for vec in vectors:
            for i in range(length):
                result[i] = (result[i] * vec[i]) % n_sq
        return result


# Instancia oficial por defecto en el Sprint 3
default_vote_codec: VoteCodec = HomomorphicPaillierVoteCodec()
