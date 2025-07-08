from fastapi import FastAPI, Request, File, UploadFile, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape
import json
import os
import uuid
import asyncio
from typing import Dict, List
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Video Captioning Tool", description="Add captions to your videos with style")

# Create necessary directories
os.makedirs("input", exist_ok=True)
os.makedirs("output", exist_ok=True)
os.makedirs("static", exist_ok=True)

# Mount static files
app.mount("/javascript", StaticFiles(directory="javascript"), name="javascript")
app.mount("/input", StaticFiles(directory="input"), name="input")
app.mount("/output", StaticFiles(directory="output"), name="output")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
template_dirs = [".", "./templates"]
env = Environment(
    loader=FileSystemLoader(template_dirs),
    autoescape=select_autoescape(['html', 'xml'])
)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"Client {client_id} connected")

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"Client {client_id} disconnected")

    async def send_personal_message(self, message: dict, client_id: str):
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(json.dumps(message))
            except:
                self.disconnect(client_id)

    async def broadcast(self, message: dict):
        for client_id, connection in self.active_connections.items():
            try:
                await connection.send_text(json.dumps(message))
            except:
                self.disconnect(client_id)

manager = ConnectionManager()

# Store processing jobs
processing_jobs: Dict[str, dict] = {}

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    template = env.get_template("index.html")
    html_content = template.render(request=request)
    return HTMLResponse(content=html_content)

@app.post("/upload-video")
async def upload_video(file: UploadFile = File(...)):
    try:
        # Generate unique filename
        file_id = str(uuid.uuid4())
        file_extension = Path(file.filename).suffix
        filename = f"{file_id}{file_extension}"
        file_path = f"input/{filename}"
        
        # Save file
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Return file info
        return {
            "file_id": file_id,
            "filename": filename,
            "original_name": file.filename,
            "size": len(content),
            "url": f"/input/{filename}"
        }
    
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail="Error uploading file")

@app.post("/process-video")
async def process_video(request: Request):
    try:
        data = await request.json()
        job_id = str(uuid.uuid4())
        
        # Store job info
        processing_jobs[job_id] = {
            "status": "queued",
            "progress": 0,
            "file_id": data.get("file_id"),
            "config": data.get("config"),
            "timestamps": []
        }
        
        # Start processing in background
        asyncio.create_task(process_video_background(job_id, data))
        
        return {"job_id": job_id}
    
    except Exception as e:
        logger.error(f"Error starting video processing: {str(e)}")
        raise HTTPException(status_code=500, detail="Error starting video processing")

async def process_video_background(job_id: str, data: dict):
    """Simulate video processing with progress updates"""
    try:
        # Update status to processing
        processing_jobs[job_id]["status"] = "processing"
        await manager.broadcast({
            "type": "job_update",
            "job_id": job_id,
            "status": "processing",
            "progress": 0,
            "message": "Starting video processing..."
        })
        
        # Simulate processing steps
        steps = [
            {"progress": 20, "message": "Extracting audio from video..."},
            {"progress": 40, "message": "Transcribing audio to text..."},
            {"progress": 60, "message": "Generating word timestamps..."},
            {"progress": 80, "message": "Applying caption styles..."},
            {"progress": 100, "message": "Finalizing video with captions..."}
        ]
        
        # Mock word timestamps
        mock_timestamps = [
            {"word": "Hello", "start": 0.5, "end": 1.0},
            {"word": "world", "start": 1.0, "end": 1.5},
            {"word": "this", "start": 2.0, "end": 2.3},
            {"word": "is", "start": 2.3, "end": 2.5},
            {"word": "a", "start": 2.5, "end": 2.6},
            {"word": "test", "start": 2.6, "end": 3.0},
            {"word": "video", "start": 3.0, "end": 3.5},
            {"word": "caption", "start": 4.0, "end": 4.5},
            {"word": "demonstration", "start": 4.5, "end": 5.5}
        ]
        
        for step in steps:
            await asyncio.sleep(2)  # Simulate processing time
            
            processing_jobs[job_id]["progress"] = step["progress"]
            
            # Add timestamps when we reach the timestamp generation step
            if step["progress"] == 60:
                processing_jobs[job_id]["timestamps"] = mock_timestamps
            
            await manager.broadcast({
                "type": "job_update",
                "job_id": job_id,
                "status": "processing",
                "progress": step["progress"],
                "message": step["message"],
                "timestamps": processing_jobs[job_id]["timestamps"] if step["progress"] >= 60 else []
            })
        
        # Mark as completed
        processing_jobs[job_id]["status"] = "completed"
        output_filename = f"output_{job_id}.mp4"
        
        await manager.broadcast({
            "type": "job_update",
            "job_id": job_id,
            "status": "completed",
            "progress": 100,
            "message": "Video processing completed successfully!",
            "output_url": f"/output/{output_filename}",
            "timestamps": processing_jobs[job_id]["timestamps"]
        })
        
    except Exception as e:
        logger.error(f"Error in background processing: {str(e)}")
        processing_jobs[job_id]["status"] = "error"
        await manager.broadcast({
            "type": "job_update",
            "job_id": job_id,
            "status": "error",
            "progress": 0,
            "message": f"Error processing video: {str(e)}"
        })

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message.get("type") == "ping":
                await manager.send_personal_message({"type": "pong"}, client_id)
            
    except WebSocketDisconnect:
        manager.disconnect(client_id)

@app.get("/job-status/{job_id}")
async def get_job_status(job_id: str):
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return processing_jobs[job_id]

@app.get("/health")
async def health_check():
    return {"status": "healthy", "active_connections": len(manager.active_connections)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)