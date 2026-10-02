from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Client
from app.services import ClientService


async def authenticate_api_key(
    session: AsyncSession,
    api_key: str,
) -> Client | None:
    service = ClientService(session)

    return await service.authenticate(api_key)