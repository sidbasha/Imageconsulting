import uuid
from datetime import datetime

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class ChangesIn(BaseModel):
    phases: dict[str, bool] = Field(default_factory=dict)
    features: dict[str, bool] = Field(default_factory=dict)

    def as_changes(self) -> dict:
        return {"phases": self.phases, "features": self.features}


class ReleaseIn(ChangesIn):
    note: str = Field(min_length=3, max_length=2000, description="Why this release is being made")
    activate_at: AwareDatetime | None = Field(default=None, description="Omit to activate now")


class RollbackIn(BaseModel):
    note: str = Field(min_length=3, max_length=2000)


class ReleaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    version: int
    status: str
    note: str
    changes: dict | None
    snapshot: dict | None
    activate_at: datetime | None
    activated_at: datetime | None
    restored_from_id: uuid.UUID | None
    created_by_id: uuid.UUID | None
    created_at: datetime


class HistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    release_id: uuid.UUID
    previous_release_id: uuid.UUID | None
    action: str
    actor_id: uuid.UUID | None
    detail: dict | None
    created_at: datetime
