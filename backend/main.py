import json
import subprocess
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

approval_queue = []

class Approval(BaseModel):
    text: str

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

@app.post("/start-dev-crew")
async def start_dev_crew(background_tasks: BackgroundTasks):
    """Launches the veteran developer crew orchestration."""
    def run_crew():
        venv_python = r"C:\Users\Sergio Ramos\Documents\LMStudioAgents\LocalAI\LocalAI\venv_stable\Scripts\python.exe"
        subprocess.Popen([venv_python, "dev_crew.py"])
    
    background_tasks.add_task(run_crew)
    return {"status": "success", "message": "Engineering Cluster Booting."}

@app.post("/show-proposal")
async def show_proposal(data: dict):
    await manager.broadcast({
        "type": "AGENT_PROPOSAL", 
        "payload": data.get("plan", "No code review text provided.")
    })
    return {"status": "PR Displayed"}

@app.post("/submit-approval")
async def submit_approval(approval: Approval):
    print(f"\n[DIRECTOR FEEDBACK]: {approval.text}")
    approval_queue.append(approval.text)
    return {"status": "success"}

@app.get("/check-approval-status")
async def check_approval():
    if approval_queue:
        return {"approved": True, "feedback": approval_queue.pop(0)}
    return {"approved": False}

@app.post("/broadcast-agent")
async def broadcast_agent(data: dict):
    await manager.broadcast({"type": "AGENT_THOUGHT", "payload": data["payload"]})
    return {"status": "sent"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    # TURN RELOAD OFF to prevent Uvicorn from killing the AI agents
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)