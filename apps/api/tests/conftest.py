"""
Configuración de Fixtures para la Suite de Pruebas de Invariantes (pytest)
"""
import uuid
from datetime import datetime, timezone
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.dependencies import get_time_provider
from app.core.security import create_access_token, get_password_hash
from app.core.time import FakeTimeProvider
from app.db.base import Base
from app.db.models.organization import Organization, OrganizationStatus, OrganizationType
from app.db.models.user import User, UserRole, UserStatus
from app.db.session import get_db_session
from app.main import app

# Motor SQLite asíncrono en memoria para pruebas veloces y aisladas
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True,
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(scope="function")
async def test_db():
    """Crea y destruye el esquema completo de base de datos en cada prueba."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def fake_time():
    """Reloj manipulable para validar transiciones temporales."""
    start_time = datetime(2026, 11, 25, 8, 0, 0, tzinfo=timezone.utc)
    return FakeTimeProvider(initial_time=start_time)


@pytest_asyncio.fixture(scope="function")
async def client(test_db: AsyncSession, fake_time: FakeTimeProvider):
    """Cliente HTTP asíncrono para interactuar con la API."""
    async def override_db():
        yield test_db

    def override_time():
        return fake_time

    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_time_provider] = override_time

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver/api/v1") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def platform_admin_user(test_db: AsyncSession) -> User:
    admin = User(
        organization_id=None,
        email="platform_admin@votoseguro.org",
        full_name="Super Administrador Plataforma",
        password_hash=get_password_hash("PlatformPassword2026!"),
        role=UserRole.PLATFORM_ADMIN,
        status=UserStatus.ACTIVE,
    )
    test_db.add(admin)
    await test_db.commit()
    await test_db.refresh(admin)
    return admin


@pytest_asyncio.fixture
async def platform_admin_token(platform_admin_user: User) -> str:
    return create_access_token(
        subject=str(platform_admin_user.id),
        role=platform_admin_user.role.value,
        organization_id=None,
    )


@pytest_asyncio.fixture
async def org1_setup(test_db: AsyncSession) -> tuple[Organization, User, str]:
    """Crea la Organización 1 ('Universidad EL GRAN ESTUDIO') y su ADMIN_GENERAL."""
    org = Organization(
        name="Universidad EL GRAN ESTUDIO",
        slug="gran-estudio",
        org_type=OrganizationType.UNIVERSITY,
        status=OrganizationStatus.ACTIVE,
        contact_email="rectorado@granestudio.edu.bo",
    )
    test_db.add(org)
    await test_db.flush()

    admin = User(
        organization_id=org.id,
        email="admin@granestudio.edu.bo",
        full_name="Rector Admin General",
        password_hash=get_password_hash("AdminGranEstudio2026!"),
        role=UserRole.ADMIN_GENERAL,
        status=UserStatus.ACTIVE,
    )
    test_db.add(admin)
    await test_db.commit()
    await test_db.refresh(org)
    await test_db.refresh(admin)

    token = create_access_token(
        subject=str(admin.id),
        role=admin.role.value,
        organization_id=str(org.id),
    )
    return org, admin, token


@pytest_asyncio.fixture
async def org2_setup(test_db: AsyncSession) -> tuple[Organization, User, str]:
    """Crea la Organización 2 ('Elecciones Ecuador') y su ADMIN_GENERAL."""
    org = Organization(
        name="Elecciones Nacionales Ecuador",
        slug="cne-ecuador",
        org_type=OrganizationType.NATIONAL,
        status=OrganizationStatus.ACTIVE,
        contact_email="contacto@cne.gob.ec",
    )
    test_db.add(org)
    await test_db.flush()

    admin = User(
        organization_id=org.id,
        email="admin@cne.gob.ec",
        full_name="Presidente CNE Ecuador",
        password_hash=get_password_hash("CneEcuador2026!"),
        role=UserRole.ADMIN_GENERAL,
        status=UserStatus.ACTIVE,
    )
    test_db.add(admin)
    await test_db.commit()
    await test_db.refresh(org)
    await test_db.refresh(admin)

    token = create_access_token(
        subject=str(admin.id),
        role=admin.role.value,
        organization_id=str(org.id),
    )
    return org, admin, token
