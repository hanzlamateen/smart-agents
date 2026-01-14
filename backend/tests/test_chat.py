import json
from unittest.mock import MagicMock, AsyncMock
from app.services.chat import ChatService
from app.routers.chat import get_chat_service

def test_chat_stream(client):
    # Mock ChatService
    mock_service = MagicMock(spec=ChatService)
    
    # Mock validate_session
    mock_service.validate_session.return_value = None
    
    # Mock get_history
    mock_service.get_history.return_value = []
    
    # Mock run_chat_stream to be an async generator
    async def mock_stream(request, history):
        yield json.dumps({"type": "text", "content": "Hello"})
        yield json.dumps({"type": "done"})
        
    mock_service.run_chat_stream = mock_stream
    
    # Override dependency
    client.app.dependency_overrides[get_chat_service] = lambda: mock_service
    
    # Create a session first needed for validation? 
    # Actually we mocked validate_session so we don't strictly need a DB session if the service is fully mocked.
    # But request object validation might require an int ID.
    
    response = client.post(
        "/chat", 
        json={"session_id": "test-session-id", "message": "Hi"},
        # TestClient handles stream?
    )
    
    # TestClient doesn't support streaming response content fully like a real browser
    # but we can check the iterator or just text.
    assert response.status_code == 200
    # The output format for SSE from TestClient usually includes the full body.
    # starlette's EventSourceResponse formats as "data: ...\n\n"
    
    assert 'data: {"type": "text", "content": "Hello"}' in response.text
    assert 'data: {"type": "done"}' in response.text
    
    # Cleanup overrides
    client.app.dependency_overrides = {}
