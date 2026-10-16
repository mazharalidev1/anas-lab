from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MetricsBatch(BaseModel):
    schema_version: int = Field(ge=1)
    agent_id: str = Field(min_length=1, max_length=128)
    hostname: str = Field(min_length=1, max_length=255)
    platform: str = Field(max_length=255)
    observed_at: datetime
    uptime_seconds: int = Field(ge=0)
    metrics: dict[str, Any]
