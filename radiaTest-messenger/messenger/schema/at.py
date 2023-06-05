from pydantic import BaseModel


class AtSchema(BaseModel):
    release_url: str
    user: str
    port: int
    password: str
    ip: str
    user_id: str
