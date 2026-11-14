from pydantic import BaseModel, Field


class ImpactNode(BaseModel):
    id: str
    kind: str
    name: str
    depth: int
    score: int = 0
    risk: str = "LOW"
    reasons: list[str] = Field(default_factory=list)
    chain: list[dict[str, str]] = Field(default_factory=list)
    criticality: int = 0
    backup_power_hours: float | None = None


class ImpactSummary(BaseModel):
    event_id: str
    event_type: str
    severity: str
    target_id: str
    impacts: list[ImpactNode]
    direct_count: int
    total_count: int
    max_depth: int
