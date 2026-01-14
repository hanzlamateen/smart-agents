def test_create_session(client):
    response = client.post("/sessions", json={"title": "Test Session"})
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Session"
    assert "id" in data

def test_get_sessions(client):
    # Create two sessions
    client.post("/sessions", json={"title": "Session 1"})
    client.post("/sessions", json={"title": "Session 2"})
    
    response = client.get("/sessions")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    # Check ordering (descending creation)
    assert data[0]["title"] == "Session 2"
    assert data[1]["title"] == "Session 1"

def test_search_sessions(client):
    client.post("/sessions", json={"title": "Apple"})
    client.post("/sessions", json={"title": "Banana"})
    
    response = client.get("/sessions?q=App")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Apple"

def test_pagination(client):
    # Create 5 sessions
    for i in range(5):
        client.post("/sessions", json={"title": f"Session {i}"})
        
    # Get first 2
    response = client.get("/sessions?limit=2")
    assert response.status_code == 200
    assert len(response.json()) == 2
    
    # Get next 2
    response = client.get("/sessions?limit=2&skip=2")
    assert response.status_code == 200
    assert len(response.json()) == 2

def test_update_session(client):
    res = client.post("/sessions", json={"title": "Old Title"})
    session_id = res.json()["id"]
    
    response = client.patch(f"/sessions/{session_id}", json={"title": "New Title"})
    assert response.status_code == 200
    assert response.json()["title"] == "New Title"
    
    # Verify persistence
    get_res = client.get(f"/sessions?q=New")
    assert len(get_res.json()) == 1
