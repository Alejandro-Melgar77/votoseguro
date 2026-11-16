"""
S3-02: Esquema de Secreto Compartido de Shamir (k de n) sobre Cuerpo Finito F_p
Permite dividir la clave privada de Paillier (p, q) entre n vocales/autoridades de la Corte Electoral,
exigiendo un quórum de al menos k fragmentos para reconstruir la clave en RAM y desbloquear
el escrutinio homomórfico oficial. Con k-1 fragmentos o menos, es matemáticamente imposible
obtener información sobre la clave de descifrado.
"""
import hashlib
import json
import re
import secrets
from typing import Any


class ShamirSecurityException(Exception):
    """Excepción base para violaciones de seguridad en el esquema de Shamir."""
    pass


class InsufficientSharesException(ShamirSecurityException):
    """Lanzada cuando se proporcionan menos de k fragmentos para la reconstrucción."""
    pass


class InvalidShareCommitmentException(ShamirSecurityException):
    """Lanzada cuando un fragmento no coincide con su compromiso criptográfico registrado."""
    pass


class CorruptedShareException(ShamirSecurityException):
    """Lanzada cuando el formato o valor de un fragmento es inválido o está corrupto."""
    pass


# Primo seguro estándar de 4097 bits para el cuerpo finito F_P
# P = 2^4096 + 1761 (número primo demostrado mediante Miller-Rabin con 40 rondas).
# Cubre con amplitud claves Paillier de 1024, 2048 y 4096 bits.
DEFAULT_SHAMIR_PRIME = (1 << 4096) + 1761


def is_probable_prime(n: int, k: int = 30) -> bool:
    """Test de primalidad Miller-Rabin determinista/probabilístico con k rondas."""
    if n < 2:
        return False
    small_primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37]
    for p in small_primes:
        if n % p == 0:
            return n == p
    r, d = 0, n - 1
    while d % 2 == 0:
        r += 1
        d //= 2
    for _ in range(k):
        a = secrets.randbelow(n - 4) + 2
        x = pow(a, d, n)
        if x == 1 or x == n - 1:
            continue
        for _ in range(r - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True


def get_prime_above(val: int) -> int:
    """Genera el siguiente número primo inmediatamente superior al valor dado."""
    cand = val + 1 if val % 2 == 0 else val + 2
    while not is_probable_prime(cand):
        cand += 2
    return cand


def resolve_prime_modulus(secret_int: int, prime: int | None = None) -> int:
    """
    Determina un cuerpo finito F_P donde P > secret_int.
    Si secret_int < DEFAULT_SHAMIR_PRIME y no se suministra otro primo, emplea el primo seguro estándar.
    Si secret_int supera ese tamaño, genera un primo mayor de manera determinista.
    """
    if prime is not None:
        if secret_int >= prime:
            raise ShamirSecurityException("El secreto es mayor o igual que el módulo primo P especificado.")
        return prime
    if secret_int < DEFAULT_SHAMIR_PRIME:
        return DEFAULT_SHAMIR_PRIME
    return get_prime_above(secret_int)


def split_secret(
    secret_int: int,
    k: int,
    n: int,
    prime: int | None = None,
) -> list[tuple[int, int]]:
    """
    Genera los n puntos del polinomio f(x) = S + a_1*x + ... + a_{k-1}*x^{k-1} mod P.
    k: Umbral mínimo de fragmentos requeridos para reconstruir.
    n: Total de fragmentos a repartir entre custodios.
    Retorna lista de pares (x_i, y_i) para x_i en {1, ..., n}.
    """
    if k < 2:
        raise ShamirSecurityException("El umbral k debe ser mayor o igual a 2.")
    if n < k:
        raise ShamirSecurityException("El número total de fragmentos n debe ser mayor o igual al umbral k.")
    if secret_int <= 0:
        raise ShamirSecurityException("El secreto a compartir debe ser un entero positivo no nulo.")

    P = resolve_prime_modulus(secret_int, prime)

    # Coeficientes aleatorios criptográficamente seguros: f(0) = S, f'(x) con coeficientes en [1, P-1]
    coeffs = [secret_int]
    for _ in range(k - 1):
        coeffs.append(secrets.randbelow(P - 1) + 1)

    shares: list[tuple[int, int]] = []
    for x in range(1, n + 1):
        y = 0
        for degree, coeff in enumerate(coeffs):
            y = (y + coeff * pow(x, degree, P)) % P
        shares.append((x, y))

    return shares


def combine_shares(
    shares: list[tuple[int, int]],
    prime: int | None = None,
    min_k: int | None = None,
) -> int:
    """
    Reconstruye el secreto original aplicando interpolación de Lagrange en x = 0 sobre F_P.
    Lanza InsufficientSharesException si se proporcionan menos de k fragmentos.
    """
    if not shares:
        raise InsufficientSharesException(
            "Se requieren al menos k fragmentos válidos de la Corte Electoral para reconstruir la clave de descifrado."
        )

    required_min = min_k if min_k is not None else 2
    if len(shares) < required_min:
        raise InsufficientSharesException(
            f"Se requieren al menos {required_min} fragmentos válidos de la Corte Electoral "
            f"para reconstruir la clave de descifrado (se recibieron {len(shares)})."
        )

    # Validar unicidad de coordenadas x
    seen_x = set()
    cleaned_shares: list[tuple[int, int]] = []
    for x, y in shares:
        if x in seen_x:
            continue
        seen_x.add(x)
        cleaned_shares.append((x, y))

    if min_k is not None and len(cleaned_shares) < min_k:
        raise InsufficientSharesException(
            f"Fragmentos duplicados detectados. Se requieren al menos {min_k} fragmentos distintos "
            f"para alcanzar el quórum (se cuentan {len(cleaned_shares)} únicos)."
        )

    # Determinar el primo del cuerpo finito
    P = prime if prime is not None else DEFAULT_SHAMIR_PRIME

    k_shares = cleaned_shares
    secret = 0
    k_len = len(k_shares)

    # Interpolación de Lagrange en x = 0: S = sum_{j=1}^k y_j * l_j(0) mod P
    for j in range(k_len):
        xj, yj = k_shares[j]
        numerator = 1
        denominator = 1
        for m in range(k_len):
            if m == j:
                continue
            xm, _ = k_shares[m]
            numerator = (numerator * (-xm)) % P
            denominator = (denominator * (xj - xm)) % P

        # Inverso modular exacto en F_P
        inv_denominator = pow(denominator, -1, P)
        lagrange_basis = (numerator * inv_denominator) % P
        secret = (secret + yj * lagrange_basis) % P

    return secret


def pack_paillier_private_key(p: int, q: int) -> int:
    """
    Empaqueta los factores primos privados de Paillier (p, q) en un entero positivo único S.
    Utiliza codificación canónica JSON serializada a bytes en orden big-endian.
    """
    payload_str = json.dumps({"p": str(p), "q": str(q)}, sort_keys=True, separators=(",", ":"))
    payload_bytes = payload_str.encode("utf-8")
    return int.from_bytes(payload_bytes, byteorder="big")


def unpack_paillier_private_key(secret_int: int) -> tuple[int, int]:
    """
    Desempaqueta el entero S recuperado mediante interpolación de Lagrange para obtener (p, q).
    Si los fragmentos eran insuficientes o adulterados, la reconstrucción falla al no poder
    decodificar el payload JSON canónico original.
    """
    try:
        byte_len = (secret_int.bit_length() + 7) // 8
        raw_bytes = secret_int.to_bytes(byte_len, byteorder="big")
        data = json.loads(raw_bytes.decode("utf-8"))
        p = int(data["p"])
        q = int(data["q"])
        if p <= 1 or q <= 1:
            raise ValueError("Primos inválidos")
        return p, q
    except Exception as exc:
        raise ShamirSecurityException(
            "Los fragmentos proporcionados no reconstruyen una clave privada Paillier válida "
            "(quórum insuficiente o fragmentos inválidos)."
        ) from exc


def format_share(index: int, k: int, n: int, y: int) -> str:
    """Formatea un fragmento institucional como token legible: VS-SHARE-{i}-{k}OF{n}-{hex(y)}."""
    return f"VS-SHARE-{index}-{k}OF{n}-{hex(y)[2:].upper()}"


def parse_share(share_val: Any) -> tuple[int, int]:
    """
    Parsea un fragmento desde cadena formateada ('VS-SHARE-1-3OF5-...') o tupla (x, y).
    """
    if isinstance(share_val, (tuple, list)) and len(share_val) == 2:
        return int(share_val[0]), int(share_val[1])

    if isinstance(share_val, str):
        share_str = share_val.strip()
        pattern = r"^VS-SHARE-(\d+)-(\d+)OF(\d+)-([0-9a-fA-F]+)$"
        match = re.match(pattern, share_str)
        if match:
            idx = int(match.group(1))
            y_hex = match.group(4)
            return idx, int(y_hex, 16)

        # Formato simple x:y_hex o x:y_int
        if ":" in share_str:
            parts = share_str.split(":", 1)
            idx = int(parts[0])
            y_str = parts[1].strip()
            y_val = int(y_str, 16) if y_str.startswith(("0x", "0X")) else int(y_str)
            return idx, y_val

    raise CorruptedShareException(f"Formato de fragmento de Shamir inválido: '{share_val}'")


def compute_share_commitment(election_id: Any, share_index: int, y_val: int) -> str:
    """
    Calcula el compromiso criptográfico SHA-256 de un fragmento de Shamir:
    SHA-256("SHAMIR_COMMIT:" || election_id || ":" || share_index || ":" || hex(y_val))
    Permite verificar matemáticamente que un fragmento entregado para el escrutinio
    corresponde exactamente al emitido durante la Ceremonia de Generación de Claves.
    """
    y_hex = hex(y_val)[2:].upper()
    data = f"SHAMIR_COMMIT:{str(election_id)}:{share_index}:{y_hex}".encode("utf-8")
    return hashlib.sha256(data).hexdigest()
