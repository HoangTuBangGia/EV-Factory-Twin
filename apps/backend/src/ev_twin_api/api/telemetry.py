from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Request, status

from ev_twin_api.api.dependencies import require_edge_telemetry_secret
from ev_twin_api.schemas.telemetry import RobotTelemetry, TelemetryIngressResponse
from ev_twin_api.services.telemetry_ingress import (
    MockSourceActiveError,
    TelemetryIngressService,
    UnknownRobotError,
)

router = APIRouter(
    prefix="/internal/v1/telemetry",
    tags=["edge"],
    dependencies=[Depends(require_edge_telemetry_secret)],
)


def get_telemetry_ingress_service(request: Request) -> TelemetryIngressService:
    return cast(TelemetryIngressService, request.app.state.telemetry_ingress_service)


TelemetryIngressServiceDep = Annotated[
    TelemetryIngressService, Depends(get_telemetry_ingress_service)
]


@router.post("", response_model=TelemetryIngressResponse)
async def ingest_telemetry(
    telemetry: RobotTelemetry,
    ingress_service: TelemetryIngressServiceDep,
) -> TelemetryIngressResponse:
    try:
        return await ingress_service.ingest(telemetry)
    except UnknownRobotError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Robot '{telemetry.robot_id}' not found",
        ) from error
    except MockSourceActiveError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Stop the mock factory before sending edge telemetry",
        ) from error
