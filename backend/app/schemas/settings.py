from pydantic import BaseModel, Field


class SettingUpdate(BaseModel):
    value: str = Field(min_length=1, max_length=1000)


class SettingOut(BaseModel):
    id: int
    key: str
    value: str
    description: str | None = None
    updated_by: int | None = None
    updated_at: str | None = None


class FileStoragePolicyOut(BaseModel):
    allowed_file_types: list[str]
    max_file_size_mb: float
    storage_provider: str
    retention_policy: str = "preserve"


class DatabaseHealthOut(BaseModel):
    status: str
    service: str = "landguard-ai"
    database: str = "neon-postgresql"
