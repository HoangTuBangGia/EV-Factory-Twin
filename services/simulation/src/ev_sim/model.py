from dataclasses import dataclass

import simpy


@dataclass
class TaskRecord:
    task_id: int
    created_at: float
    started_at: float
    completed_at: float

    @property
    def cycle_time(self) -> float:
        return self.completed_at - self.created_at

    @property
    def waiting_time(self) -> float:
        return self.started_at - self.created_at


class FactorySimulation:
    def __init__(
        self,
        env: simpy.Environment,
        num_robots: int,
        travel_time: float,
        loading_time: float,
    ) -> None:
        self.env = env
        self.robots = simpy.Resource(env, capacity=num_robots)
        self.travel_time = travel_time
        self.loading_time = loading_time
        self.records: list[TaskRecord] = []

    def process_task(self, task_id: int):
        created_at = self.env.now

        with self.robots.request() as request:
            yield request

            started_at = self.env.now

            yield self.env.timeout(self.loading_time)
            yield self.env.timeout(self.travel_time)
            yield self.env.timeout(self.loading_time)

            completed_at = self.env.now

            self.records.append(
                TaskRecord(
                    task_id=task_id,
                    created_at=created_at,
                    started_at=started_at,
                    completed_at=completed_at,
                )
            )
