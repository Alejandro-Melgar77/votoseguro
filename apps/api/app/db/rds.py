"""Load rotated RDS passwords when opening database connections."""
import asyncio
import json
import time

import asyncpg
import boto3
from botocore.config import Config

from app.core.config import settings


class RdsPasswordProvider:
    def __init__(self):
        self._password = None
        self._expires = 0.0
        self._lock = asyncio.Lock()

    async def get(self, force=False):
        async with self._lock:
            if not force and self._password and self._expires > time.monotonic():
                return self._password
            def fetch():
                client = boto3.client('secretsmanager', config=Config(
                    connect_timeout=3, read_timeout=3, retries={'max_attempts': 2}))
                return json.loads(client.get_secret_value(
                    SecretId=settings.DATABASE_PASSWORD_SECRET_ARN)['SecretString'])['password']
            self._password = await asyncio.to_thread(fetch)
            self._expires = time.monotonic() + 60
            return self._password


password_provider = RdsPasswordProvider()


async def connect_rds():
    import ssl
    params = dict(host=settings.PGHOST, port=settings.PGPORT, user=settings.PGUSER,
        database=settings.PGDATABASE, ssl=ssl.create_default_context(
            cafile=settings.DATABASE_SSL_CA_FILE))
    try:
        return await asyncpg.connect(**params, password=await password_provider.get())
    except asyncpg.InvalidPasswordError:
        # RDS may have rotated the secret since the last successful connection.
        return await asyncpg.connect(**params, password=await password_provider.get(force=True))
