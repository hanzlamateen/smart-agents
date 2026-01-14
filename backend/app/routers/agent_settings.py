from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as sqlSession
from ..infra.database import get_db
from ..schemas import AgentSettingsUpdate, AgentSettingsResponse
from ..services.agent_settings import AgentSettingsService

router = APIRouter(prefix="/agent-settings", tags=["settings"])

def get_settings_service(db: sqlSession = Depends(get_db)) -> AgentSettingsService:
    return AgentSettingsService(db)

@router.get("", response_model=AgentSettingsResponse)
def get_settings(service: AgentSettingsService = Depends(get_settings_service)):
    """
    Retrieve current agent settings.
    """
    return service.get_settings()

@router.post("", response_model=AgentSettingsResponse)
def update_settings(settings: AgentSettingsUpdate, service: AgentSettingsService = Depends(get_settings_service)):
    """
    Update agent settings.
    
    Updates the configuration stored in the database.
    """
    return service.update_settings(settings)
