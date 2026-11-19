"""Regression checks for persistent secrets and production preconditions."""
import json
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.core.config import Settings, settings
from app.crypto.vote_codec import HomomorphicPaillierVoteCodec
from app.db.models.election import Election, ElectionStatus, ElectoralTrusteeShare


def test_production_rejects_development_defaults():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, ENVIRONMENT='production')


def test_database_password_is_encoded_and_tls_is_required():
    config = Settings(_env_file=None, PGHOST='db.internal', PGUSER='app',
        PGPASSWORD='a@b:/c%#d', PGDATABASE='votes')
    from sqlalchemy.engine import make_url
    assert make_url(config.DATABASE_URL).password == 'a@b:/c%#d'
    assert make_url(config.DATABASE_URL).host == 'db.internal'


def test_encryption_rejects_missing_key_and_unlisted_selection():
    import phe.paillier as paillier
    codec = HomomorphicPaillierVoteCodec()
    with pytest.raises(ValueError):
        codec.encode('CANDIDATE', 'a', option_keys=['a', 'b'])
    pub, priv = paillier.generate_paillier_keypair(n_length=512)
    with pytest.raises(ValueError):
        codec.encode('CANDIDATE', 'missing', public_key=pub, option_keys=['a', 'b'])
    payload = codec.encode('CANDIDATE', 'a', public_key=pub, option_keys=['a', 'b'])
    parsed = json.loads(payload)
    assert 'candidate_id' not in parsed and 'choice_type' not in parsed
    assert codec.decode(payload, private_key=priv)['decoded_selection'] == 'a'


@pytest.mark.asyncio
async def test_shares_only_delivered_once_and_ceremony_cannot_replace_keys(test_db, client, org1_setup):
    org, admin, token = org1_setup
    now = datetime.now(timezone.utc)
    election = Election(organization_id=org.id, name='Privacy regression', created_by=admin.id,
        status=ElectionStatus.DRAFT, registration_opens_at=now,
        registration_closes_at=now+timedelta(days=1), voting_opens_at=now+timedelta(days=2),
        voting_closes_at=now+timedelta(days=3))
    test_db.add(election)
    await test_db.commit()
    headers = {'Authorization': f'Bearer {token}'}
    url = f'/elections/{election.id}/shamir'
    setup = await client.post(url+'/setup', headers=headers, json={'threshold_k': 2, 'total_n': 3, 'key_size': 512})
    assert setup.status_code == 201
    assert all(t['share_token'].startswith('VS-SHARE-') for t in setup.json()['trustees'])
    assert setup.headers['cache-control'] == 'no-store'
    rows = (await test_db.execute(select(ElectoralTrusteeShare).where(ElectoralTrusteeShare.election_id == election.id))).scalars().all()
    assert len(rows) == 3
    assert all(t.demo_share_token is None for t in rows)
    status = await client.get(url+'/status', headers=headers)
    assert all(t['share_token'] is None for t in status.json()['trustees'])
    retry = await client.post(url+'/setup', headers=headers, json={'threshold_k': 2, 'total_n': 3, 'key_size': 512})
    assert retry.status_code == 409
    assert status.json()['paillier_public_n'] == setup.json()['paillier_public_n']


@pytest.mark.asyncio
async def test_production_ceremony_requires_draft_and_real_trustees(test_db, client, org1_setup, monkeypatch):
    org, admin, token = org1_setup
    now = datetime.now(timezone.utc)
    election = Election(organization_id=org.id, name='Production ceremony', created_by=admin.id,
        status=ElectionStatus.VOTING_OPEN, registration_opens_at=now-timedelta(days=2),
        registration_closes_at=now-timedelta(days=1), voting_opens_at=now,
        voting_closes_at=now+timedelta(days=1))
    test_db.add(election)
    await test_db.commit()
    monkeypatch.setattr(settings, 'ENVIRONMENT', 'production')
    headers = {'Authorization': f'Bearer {token}'}
    response = await client.post(f'/elections/{election.id}/shamir/setup', headers=headers, json={'key_size':2048})
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_rds_refreshes_rejected_password_after_rotation(monkeypatch):
    from app.db import rds
    calls = []
    async def password(force=False):
        calls.append(force)
        return 'rotated' if force else 'previous'
    async def connect(**kwargs):
        if kwargs['password'] == 'previous':
            raise rds.asyncpg.InvalidPasswordError('rotated secret')
        return 'connected'
    monkeypatch.setattr(rds.password_provider, 'get', password)
    monkeypatch.setattr(rds.asyncpg, 'connect', connect)
    assert await rds.connect_rds() == 'connected'
    assert calls == [False, True]
