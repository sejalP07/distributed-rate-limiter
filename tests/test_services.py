import pytest
from sqlalchemy import delete

from app.database import AsyncSessionLocal
from app.models import Client
from app.services import ClientService


@pytest.mark.anyio
async def test_create_client():
    async with AsyncSessionLocal() as session:
        service = ClientService(session)

        result = await service.create_client(
            "Service Test Client"
        )

        assert result.client.id is not None
        assert (
            result.client.name
            == "Service Test Client"
        )

        assert result.api_key.startswith(
            "rl_"
        )

        assert (
            result.client.api_key_hash
            != result.api_key
        )

        assert len(
            result.client.api_key_hash
        ) == 64

        await session.execute(
            delete(Client).where(
                Client.id
                == result.client.id
            )
        )
        await session.commit()


@pytest.mark.anyio
async def test_authenticate_valid_key():
    async with AsyncSessionLocal() as session:
        service = ClientService(session)

        created = await (
            service.create_client(
                "Authentication Client"
            )
        )

        authenticated = await (
            service.authenticate(
                created.api_key
            )
        )

        assert authenticated is not None
        assert (
            authenticated.id
            == created.client.id
        )

        await session.execute(
            delete(Client).where(
                Client.id
                == created.client.id
            )
        )
        await session.commit()


@pytest.mark.anyio
async def test_authenticate_invalid_key():
    async with AsyncSessionLocal() as session:
        service = ClientService(session)

        created = await (
            service.create_client(
                "Invalid Key Client"
            )
        )

        authenticated = await (
            service.authenticate(
                "rl_invalid_key"
            )
        )

        assert authenticated is None

        await session.execute(
            delete(Client).where(
                Client.id
                == created.client.id
            )
        )
        await session.commit()


@pytest.mark.anyio
async def test_inactive_client_cannot_authenticate():
    async with AsyncSessionLocal() as session:
        service = ClientService(session)

        created = await (
            service.create_client(
                "Inactive Client"
            )
        )

        created.client.is_active = False

        await session.commit()

        authenticated = await (
            service.authenticate(
                created.api_key
            )
        )

        assert authenticated is None

        await session.execute(
            delete(Client).where(
                Client.id
                == created.client.id
            )
        )
        await session.commit()


@pytest.mark.anyio
async def test_empty_client_name_is_rejected():
    async with AsyncSessionLocal() as session:
        service = ClientService(session)

        with pytest.raises(
            ValueError,
            match="name must not be empty",
        ):
            await service.create_client(
                "   "
            )