from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Client


class ClientRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        name: str,
        api_key_hash: str,
        is_active: bool = True,
    ) -> Client:
        client = Client(
            name=name,
            api_key_hash=api_key_hash,
            is_active=is_active,
        )

        self.session.add(client)

        await self.session.commit()
        await self.session.refresh(client)

        return client

    async def get_by_api_key_hash(
        self,
        api_key_hash: str,
    ) -> Client | None:
        result = await self.session.execute(
            select(Client).where(
                Client.api_key_hash == api_key_hash
            )
        )

        return result.scalar_one_or_none()

    async def get_by_id(
        self,
        client_id: int,
    ) -> Client | None:
        result = await self.session.execute(
            select(Client).where(
                Client.id == client_id
            )
        )

        return result.scalar_one_or_none()