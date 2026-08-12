from pydantic import BaseModel


class MockControlResponse(BaseModel):
    running: bool
    tick_count: int
    simulated_elapsed_seconds: float
