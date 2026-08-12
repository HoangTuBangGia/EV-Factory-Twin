from pydantic import BaseModel, Field


class Station(BaseModel):
    id: str
    name: str
    type: str
    x: float
    y: float


class FactoryLayout(BaseModel):
    width_m: float
    height_m: float
    stations: list[Station]


class MockFactoryConfig(BaseModel):
    robot_count: int = Field(default=5, ge=1, le=10)
    task_interval_seconds: float = Field(default=8.0, ge=1.0, le=60.0)
    robot_speed_mps: float = Field(default=1.2, ge=0.1, le=3.0)
    simulation_speed: float = Field(default=1.0, ge=0.25, le=10.0)
    low_battery_threshold: float = Field(default=20.0, ge=0, le=100)
