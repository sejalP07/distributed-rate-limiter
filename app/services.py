from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.api_key import (
    generate_api_key,
    hash_api_key,
    verify_api_key,
)
from app.models import Client
from app.repositories import ClientRepository


@dataclass(frozen=True)
class CreatedClient:
    client: Client
    api_key: str


class ClientService:
    def __init__(
        self,
        session: AsyncSession,
    ):
        self.repository = ClientRepository(
            session
        )

    async def create_client(
        self,
        name: str,
    ) -> CreatedClient:
        """
        Generate an API key, store only its hash,
        and return the plaintext key once.
        """

        if not name.strip():
            raise ValueError(
                "name must not be empty"
            )

        api_key = generate_api_key()

        api_key_hash = hash_api_key(
            api_key
        )

        client = await self.repository.create(
            name=name.strip(),
            api_key_hash=api_key_hash,
        )

        return CreatedClient(
            client=client,
            api_key=api_key,
        )

    async def authenticate(
        self,
        api_key: str,
    ) -> Client | None:
        """
        Authenticate an API key and return its
        active client.
        """

        if not api_key:
            return None

        api_key_hash = hash_api_key(
            api_key
        )

        client = await (
            self.repository
            .get_by_api_key_hash(
                api_key_hash
            )
        )

        if client is None:
            return None

        if not client.is_active:
            return None

        if not verify_api_key(
            api_key,
            client.api_key_hash,
        ):
            return None

        return client