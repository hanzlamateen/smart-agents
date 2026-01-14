# Smart Agents

This repository contains the **Smart Agents** service. It features a scalable **Orchestrator-Worker Architecture** that spawns isolated Docker containers for each user session, enabling secure and concurrent remote desktop agent interaction.

The system is composed of:

1. **Backend (Orchestrator)**: Manages sessions, keys, and agent logic (FastAPI).
2. **Worker Nodes**: Isolated environments (Ubuntu + X11 + VNC) where the agent operates.
3. **Frontend**: React-based UI for chat and VNC interaction.

## 🚀 Key Features

* **Secure Isolation**: Each session runs in a dedicated *Worker Container*, isolated from the host and other sessions.
* **SSH-Based Control**: The Backend connects to Workers via secure, per-session SSH keys to execute agent commands (Bash, Computer Control).
* **Dynamic Scaling**: Workers are spawned on-demand and terminated when the session ends.
* **Session Management**: Create, view, update, and search chat sessions with efficient pagination.
* **Real-time Interaction**:
  * **VNC**: Built-in VNC capabilities (via noVNC) allow users to watch the agent work in real-time.
  * **Chat**: Streaming responses via Server-Sent Events (SSE).
* **Data Persistence**: MySQL database stores session history, messages, and state.
* **Robustness**:
  * Auto-recovery for detached instances.
  * Persistent session history (MySQL).
  * Health checks and timeout handling.
* **Resilience**: Robust error handling for network interruptions, detached instances, and tool failures.

## 📊 System Architecture

The following sequence diagram illustrates the interaction between the User, Frontend, Orchestrator (Backend), Workers and the AI Model during a chat session. The architecture decouples the *Brain* (Backend) from the *Body* (Worker). The Backend runs the agent loop and tool logic, while the commands on the Worker are executed through SSH.

```mermaid
sequenceDiagram
    actor User
    participant Frontend
    participant Backend as Backend (Orchestrator)
    participant DB as MySQL
    participant Worker as Worker Container
    participant LLM as Anthropic Claude
    participant S3 as MinIO

    User->>Frontend: Creates Session
    Frontend->>Backend: POST /sessions
    Backend->>DB: Store Session
    
    Frontend->>Backend: POST /sessions/{id}/instance
    Backend->>Backend: Generate SSH Keypair
    Backend->>Docker: Spawn "worker-{id}" (Inject PubKey)
    activate Worker
    Backend->>Worker: Wait for SSH (Port 22) & VNC (Port 5900/6080)
    Backend-->>Frontend: Instance Ready (VNC URL)

    User->>Frontend: Send "Open Firefox"
    Frontend->>Backend: POST /chat
    
    loop Agent Loop (on Backend)
        Backend->>LLM: Send History
        LLM-->>Backend: Tool Call: computer(action="screenshot")
        
        Backend->>Worker: SSH Exec: "scrot /tmp/s.png"
        Worker-->>Backend: Image Data (via SFTP/Cat)
        Backend->>S3: Upload Screenshot
        
        Backend->>LLM: Tool Result (Image)
        LLM-->>Backend: Next Action (e.g. mouse_move)
        Backend-->>Frontend: Stream Response (SSE)
    end
    
    deactivate Worker
```

## 🛠️ Technology Stack

* **Backend**: Python 3.11+, FastAPI, SQLAlchemy (MySQL), `asyncssh` (for secure worker control), boto3 (S3/MinIO), Poetry, Pydantic.
* **Worker**: Ubuntu 22.04 Base, X11/XVFB, OpenSSH Server, x11vnc, noVNC, Tint2.
* **Frontend**: React, Vite, TailwindCSS.
* **Infrastructure**:
  * **Docker Compose**: Service orchestration.
  * **MySQL**: Relational data (Sessions, Messages, Instances).
  * **MinIO**: S3-compatible object storage (Screenshots).
* **AI Model**: Anthropic Claude.

## ⚙️ Configuration

Create a `.env` file in the root.

```env
# Security (Required for Key Encryption)
SSH_ENCRYPTION_KEY=... (Generate using fernet)
```

Create a `.env` file in `backend/.env`.

These variables are optional, and will be set to default values if not provided.

```env
# API Key (if using Anthropic directly)
ANTHROPIC_API_KEY=sk-ant-api03-...

# Security (Required for Key Encryption)
SSH_ENCRYPTION_KEY=... (Generate using fernet)

# Database
DATABASE_URL=mysql+pymysql://user:password@localhost/smart_agents

# Storage (MinIO/S3) for screenshots
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET_NAME=smart-agents-images
S3_PUBLIC_URL=http://localhost:9000

# Network Config
VNC_PORT_START=6081
VNC_PORT_END=6100
```

## 🚀 Getting Started

### 1. Build and Run

The solution uses two distinct images: one for the backend api and one for the worker environment.

```bash
# Build both images and start the stack
docker-compose up --build
```

### 2. Access

* **Frontend**: <http://localhost:3000>
* **Backend Docs**: <http://localhost:8080/docs>
* **MinIO Console**: <http://localhost:9001> (user/pass: minioadmin)

### 3. Usage

1. Open the Frontend.
2. Create a **New Agent Task**.
3. The Orchestrator will spawn a dedicated worker container (e.g., `worker-{session_id}`).
4. Wait for the Worker to spawn (Status: "Running").
5. Interact with the agent via chat. The VNC screen will automatically connect.
6. Chat in the right panel. Everything happens inside the isolated container.

## 📂 Project Structure

```
.
├── backend/                # Main FastAPI Application (Orchestrator & Logic)
│   ├── app/
│   │   ├── core/           # Config, Crypto, Logging
│   │   ├── infra/          # Infrastructure (Database, S3)
│   │   ├── models/         # SQLAlchemy Database Models
│   │   ├── routers/        # API Endpoints (Sessions, Instance, Chat)
│   │   ├── schemas/        # Pydantic Data Schemas
│   │   ├── services/       # Business Logic Layer (InstanceService (Spawning), ChatService)
│   │   ├── tools/          # Agent Tools (SSH-based implementation of Computer, Bash, Editor)
│   │   └── loop.py         # Main Agent Sampling Loop
│   │   └── main.py         # Application Entrypoint
│   └── Dockerfile          # Backend Image
├── worker/                 # Worker Environment
│   ├── image/              # Startup scripts (entrypoint, tint2, vnc)
│   └── Dockerfile          # Worker Image (Ubuntu)
├── frontend/               # React UI
└── docker-compose.yml      # Service Stack
```

## 🔒 Security Notes

* **SSH Isolation**: Workers are controlled exclusively via SSH. Each session has a unique keypair generated at runtime. Private keys are encrypted at rest in the DB using Fernet.
* **Network Segregation**: Workers are on an internal docker network. Only VNC ports are exposed to the host (bound to localhost by default configuration).
* **Ephemeral Environments**: Workers are destroyed when the session is closed, ensuring no state leakage between tasks.
* **Key Management**: Keys should be set in `.env` or passed via Agent Settings UI. In future it should be stored in some secure vault like AWS secrets manager, GCS secrets manager, etc.
* **Validation**: All inputs are validated using Pydantic schemas.
* **SQL Injection**: Prevented using SQLAlchemy ORM parameterization.
* **VNC Security**: Right now, anyone who knows the host IP and the dynamically assigned port can view the desktop. We could auto-generate a VNC password per session and pass it to the frontend.
* **Privileged Access**: The Orchestrator requires access to `/var/run/docker.sock` to spawn siblings.
* **Networking**: Workers are attached to the same Docker network `smart_agents_net` to communicate with the backend.
