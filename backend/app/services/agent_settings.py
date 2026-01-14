from sqlalchemy.orm import Session
from ..models import AgentSettings
from ..schemas.agent_settings import AgentSettingsUpdate, AgentSettingsResponse
from ..core.config import settings as app_settings

class AgentSettingsService:
    def __init__(self, db: Session):
        self.db = db

    def get_settings(self) -> AgentSettingsResponse:
        # Get from DB (create if not exists)
        db_settings = self.db.query(AgentSettings).filter(AgentSettings.id == 1).first()
        if not db_settings:
            db_settings = AgentSettings(id=1)
            self.db.add(db_settings)
            self.db.commit()
            self.db.refresh(db_settings)
            
        # Get API key from file/env
        api_key = app_settings.get_anthropic_api_key()
        
        # Merge
        response = AgentSettingsResponse.model_validate(db_settings)
        response.api_key = api_key
        return response

    def update_settings(self, settings_in: AgentSettingsUpdate) -> AgentSettingsResponse:
        # Update API ID
        if settings_in.api_key is not None:
            app_settings.save_anthropic_api_key(settings_in.api_key)
            
        # Update DB
        db_settings = self.db.query(AgentSettings).filter(AgentSettings.id == 1).first()
        if not db_settings:
            db_settings = AgentSettings(id=1)
            self.db.add(db_settings)
            
        update_data = settings_in.model_dump(exclude={"api_key"}, exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_settings, key, value)
            
        self.db.add(db_settings)
        self.db.commit()
        self.db.refresh(db_settings)
        
        # Return full updated
        return self.get_settings()
