"""
Esquemas Pydantic para la Ceremonia de Claves de Shamir y Escrutinio Homomórfico (S3-01 y S3-02)
"""
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, EmailStr


class TrusteeConfig(BaseModel):
    trustee_name: str = Field(..., min_length=2, max_length=150)
    trustee_email: EmailStr = Field(..., max_length=255)


class TrusteeShareItem(BaseModel):
    share_index: int
    trustee_name: str
    trustee_email: str
    commitment_hash: str
    share_token: str | None = None
    submitted_for_tally: bool = False
    submitted_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ShamirSetupRequest(BaseModel):
    key_size: int = Field(default=2048, description="Tamaño de clave Paillier en bits (1024 o 2048)")
    threshold_k: int = Field(default=3, ge=2, description="Umbral mínimo de custodios requeridos (k)")
    total_n: int = Field(default=5, ge=2, le=20, description="Total de custodios institucionales (n)")
    trustees: list[TrusteeConfig] | None = Field(
        default=None,
        description="Lista de custodios electorales. Si es None, se asignan 5 vocales institucionales por defecto."
    )


class ShamirSetupResponse(BaseModel):
    election_id: uuid.UUID
    encryption_scheme: str
    paillier_public_n: str
    paillier_key_size: int
    threshold_k: int
    total_n: int
    key_ceremony_hash: str
    trustees: list[TrusteeShareItem]
    message: str = "Ceremonia de generación de claves y reparto de fragmentos completada exitosamente."


class ShamirUnlockRequest(BaseModel):
    shares: list[str] = Field(
        ...,
        min_length=1,
        description="Lista de fragmentos institucionales aportados por los vocales (tokens VS-SHARE-... o x:y)."
    )


class ShamirUnlockResponse(BaseModel):
    election_id: uuid.UUID
    status: str
    tally_ceremony_hash: str
    decrypted_cells_count: int
    suppressed_cells_count: int
    total_ballots_tallied: int
    message: str = "Escrutinio oficial descifrado y publicado exitosamente mediante quórum de Shamir."


class CeremonyStatusResponse(BaseModel):
    election_id: uuid.UUID
    encryption_scheme: str
    paillier_public_n: str | None
    paillier_key_size: int
    threshold_k: int
    total_n: int
    key_ceremony_completed: bool
    key_ceremony_hash: str | None
    tally_ceremony_completed: bool
    tally_ceremony_hash: str | None
    election_status: str
    trustees: list[TrusteeShareItem]
