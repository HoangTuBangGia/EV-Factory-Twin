from pydantic import BaseModel


class FactoryMetrics(BaseModel):
    completed_tasks: int
    throughput_per_hour: float
    average_cycle_time_seconds: float
    active_tasks: int
    queued_tasks: int
    starvation_events: int
    fleet_utilization_percent: float
