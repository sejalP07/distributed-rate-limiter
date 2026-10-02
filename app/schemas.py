from pydantic import BaseModel, Field


class CreateClientRequest(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=100,
    )


class CreateClientResponse(BaseModel):
    id: int
    name: str
    api_key: str