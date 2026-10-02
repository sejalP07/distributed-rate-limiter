import pytest

from app.database import check_database_connection


@pytest.mark.anyio
async def test_database_connection():
    assert await check_database_connection() is True