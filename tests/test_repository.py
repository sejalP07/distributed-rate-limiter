import pytest
from sqlalchemy import delete

from app.api_key import (
    generate_api_key,
    hash_api_key,
)
from app.database import AsyncSessionLocal
from app.models import Client
from app.repositories import ClientRepository


@pytest.mark.anyio
async def test_create_client():
    api_key = generate_api_key()
    api_key_hash = hash_api_key(api_key)

    async with AsyncSessionLocal() as session:
        repository = ClientRepository(session)

        client = await repository.create(
            name="Test Client",
            api_key_hash=api_key_hash,
        )

        assert client.id is not None
        assert client.name == "Test Client"
        assert client.api_key_hash == api_key_hash
        assert client.is_active is True

        await session.execute(
            delete(Client).where(
                Client.id == client.id
            )
        )
        await session.commit()


@pytest.mark.anyio
async def test_find_client_by_api_key_hash():
    api_key = generate_api_key()
    api_key_hash = hash_api_key(api_key)

    async with AsyncSessionLocal() as session:
        repository = ClientRepository(session)

        client = await repository.create(
            name="Lookup Client",
            api_key_hash=api_key_hash,
        )

        found = await (
            repository.get_by_api_key_hash(
                api_key_hash
            )
        )

        assert found is not None
        assert found.id == client.id
        assert found.name == "Lookup Client"

        await session.execute(
            delete(Client).where(
                Client.id == client.id
            )
        )
        await session.commit()


@pytest.mark.anyio
async def test_find_client_by_id():
    api_key = generate_api_key()
    api_key_hash = hash_api_key(api_key)

    async with AsyncSessionLocal() as session:
        repository = ClientRepository(session)

        client = await repository.create(
            name="ID Lookup Client",
            api_key_hash=api_key_hash,
        )

        found = await repository.get_by_id(
            client.id
        )

        assert found is not None
        assert found.id == client.id

        await session.execute(
            delete(Client).where(
                Client.id == client.id
            )
        )
        await session.commit()


@pytest.mark.anyio
async def test_missing_api_key_hash_returns_none():
    async with AsyncSessionLocal() as session:
        repository = ClientRepository(session)

        found = await repository.get_by_api_key_hash(
            "does-not-exist"
        )

        assert found is None