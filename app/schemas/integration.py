from pydantic import BaseModel

class LinkAccount(BaseModel):
    provider: str  # github, slack, etc.
    provider_id: str