from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..infra.database import get_db
from ..services.instance import InstanceService
from ..schemas.instance import InstanceResponse
from sse_starlette.sse import EventSourceResponse

router = APIRouter(prefix="/sessions/{session_id}/instance", tags=["instance"])

def get_instance_service(db: Session = Depends(get_db)) -> InstanceService:
    return InstanceService(db)

@router.get("", response_model=InstanceResponse)
async def get_session_instance(
    session_id: str,
    service: InstanceService = Depends(get_instance_service)
):
    """
    Stream the status of the worker instance for a session (SSE).

    This endpoint returns a Server-Sent Events (SSE) stream.
    1. Polling is done internally by the server.
    2. Yields a JSON payload with the instance status (pending -> running).
    3. The stream closes automatically when the instance becomes 'running' 
       or if a timeout (60s) occurs.
    """
    return EventSourceResponse(service.monitor_instance(session_id))

@router.post("", response_model=InstanceResponse)
def spawn_session_instance(
    session_id: str,
    service: InstanceService = Depends(get_instance_service)
):
    """
    Explicitly spawn/start the worker instance for this session.
    """
    return service.spawn_instance(session_id)
