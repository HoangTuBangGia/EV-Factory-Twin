import pytest
from ev_twin_api.schemas.robot import Robot
from httpx2 import AsyncClient


@pytest.mark.asyncio
async def test_list_robots_returns_five_robots(client: AsyncClient) -> None:
    response = await client.get("/api/v1/robots")

    assert response.status_code == 200

    robots = [Robot.model_validate(item) for item in response.json()]
    assert len(robots) == 5
    assert {robot.id for robot in robots} == {f"AMR-{i:02d}" for i in range(1, 6)}


@pytest.mark.asyncio
async def test_get_robot_by_id(client: AsyncClient) -> None:
    response = await client.get("/api/v1/robots/AMR-01")

    assert response.status_code == 200
    robot = Robot.model_validate(response.json())
    assert robot.id == "AMR-01"


@pytest.mark.asyncio
async def test_get_unknown_robot_returns_404(client: AsyncClient) -> None:
    response = await client.get("/api/v1/robots/AMR-99")

    assert response.status_code == 404
    assert response.json() != {}
