from fastapi import FastAPI, Request, Response, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, JSONResponse
from agents.text_agent import TextAgent
from agents.imagegen_agent import ImageGenAgent
from agents.object_detection_agent import ObjectDetectionAgent
from agents.rag_agent import RagAgent
from agents.web_agent import WebAgent
from agents.local_agent import LocalAgent
from agents.live_agent import LiveAgent
from agents.dataframe_agent import DataFrameAgent
from pydantic import BaseModel
import os
from dotenv import load_dotenv
import json
import asyncio
from typing import Dict, Optional
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize templates
templates = Jinja2Templates(directory="templates")

# Store user sessions with timestamps
user_sessions: Dict[str, tuple[TextAgent, datetime]] = {}
local_sessions: Dict[str, tuple[LocalAgent, datetime]] = {}  # Add local sessions dictionary
dataframe_sessions: Dict[str, DataFrameAgent] = {}  # Store DataFrameAgent sessions
rag_agent = RagAgent()  # Initialize RAG agent
live_agent = LiveAgent()  # Initialize live agent instance

class ChatMessage(BaseModel):
    message: str = ""
    session_id: str = None
    is_image_mode: bool = False
    is_video_mode: bool = False
    is_rag_mode: bool = False
    is_web_mode: bool = False
    is_local_mode: bool = False
    audio_data: Optional[str] = None
    image_data: Optional[str] = None

def cleanup_old_sessions():
    """Remove sessions older than 1 hour"""
    current_time = datetime.now()
    expired_sessions = [
        session_id for session_id, (_, timestamp) in user_sessions.items()
        if current_time - timestamp > timedelta(hours=1)
    ]
    for session_id in expired_sessions:
        del user_sessions[session_id]
        
    # Also cleanup local sessions
    expired_local_sessions = [
        session_id for session_id, (_, timestamp) in local_sessions.items()
        if current_time - timestamp > timedelta(hours=1)
    ]
    for session_id in expired_local_sessions:
        del local_sessions[session_id]

@app.get("/")
async def root(request: Request):
    # Clean up old sessions on page load
    cleanup_old_sessions()
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/chat")
async def chat(message: ChatMessage):
    try:
        if message.is_web_mode:
            # Use WebAgent for web search
            web_agent = WebAgent()
            async def generate_response():
                async for chunk in web_agent.process_web_query(message.message):
                    if chunk.strip():
                        yield json.dumps({"chunk": chunk}, ensure_ascii=False) + "\n"
            return StreamingResponse(generate_response(), media_type="application/x-ndjson")
        elif message.is_rag_mode:
            # Check if we have a DataFrame agent for this session
            if message.session_id in dataframe_sessions:
                df_agent = dataframe_sessions[message.session_id]
                async def generate_response():
                    async for response in df_agent.analyze(message.message):
                        yield response + "\n"  # Response is already JSON formatted
                return StreamingResponse(generate_response(), media_type="application/x-ndjson")
            else:
                # Use RAG agent for non-CSV files
                answer = await rag_agent.answer_question(message.message, message.session_id)
                async def generate_response():
                    yield answer + "\n"
                return StreamingResponse(generate_response(), media_type="application/x-ndjson")
        elif message.is_video_mode and message.audio_data and message.image_data:
            # Use ObjectDetectionAgent for audio + image input
            object_detection_agent = ObjectDetectionAgent()
            async def generate_response():
                async for chunk in object_detection_agent.process_input(message.audio_data, message.image_data):
                    yield chunk + "\n"
                        
            return StreamingResponse(
                generate_response(),
                media_type="application/x-ndjson"
            )
        elif message.is_image_mode:
            # Use ImageGenAgent for image generation
            image_agent = ImageGenAgent()
            async def generate_response():
                async for chunk in image_agent.generate(message.message):
                    if chunk.strip():
                        yield json.dumps({"chunk": chunk}, ensure_ascii=False) + "\n"
                        
            return StreamingResponse(
                generate_response(),
                media_type="application/x-ndjson"
            )
        elif message.is_local_mode:
            # Only use local mode if RAG mode is not active
            if not message.session_id or message.session_id not in local_sessions:
                local_sessions[message.session_id] = (LocalAgent(), datetime.now())
            else:
                agent, _ = local_sessions[message.session_id]
                local_sessions[message.session_id] = (agent, datetime.now())
            
            local_agent = local_sessions[message.session_id][0]
            
            async def generate_response():
                async for chunk in local_agent.get_streaming_response(message.message, message.session_id):
                    if chunk.strip():
                        yield json.dumps({"chunk": chunk}, ensure_ascii=False) + "\n"
            return StreamingResponse(generate_response(), media_type="application/x-ndjson")
        else:
            # Get or create session for text chat
            if not message.session_id or message.session_id not in user_sessions:
                user_sessions[message.session_id] = (TextAgent(), datetime.now())
            else:
                agent, _ = user_sessions[message.session_id]
                user_sessions[message.session_id] = (agent, datetime.now())
            
            text_agent = user_sessions[message.session_id][0]
            
            async def generate_response():
                async for chunk in text_agent.get_streaming_response(message.message):
                    if chunk.strip():
                        yield json.dumps({"chunk": chunk}, ensure_ascii=False) + "\n"
                    
            return StreamingResponse(
                generate_response(),
                media_type="application/x-ndjson"
            )
    except Exception as e:
        print(f"Error processing chat: {e}")
        return StreamingResponse(
            iter([json.dumps({"error": "Sorry, I couldn't process your request."})]),
            status_code=500
        )

@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    session_id: str = Form(...)
):
    try:
        # Read file content
        file_content = await file.read()
        
        if not session_id:
            raise ValueError("Session ID is required")
            
        print(f"Processing upload for session: {session_id}")
        
        # Process document using RAG agent
        result = await rag_agent.process_document(
            file_content=file_content,
            filename=file.filename,
            session_id=session_id
        )
        
        # If it's a CSV file, store the agent in dataframe_sessions
        if result.get("agent") == "dataframe":
            # Use DataFrameAgent
            df_agent = DataFrameAgent()
            if await df_agent.load_dataframe(file_content, file.filename):
                dataframe_sessions[session_id] = df_agent
                return JSONResponse(content={"status": "success", "message": "CSV file loaded successfully"})
            else:
                raise Exception("Failed to load CSV file")
        
        return JSONResponse(content={"status": "success", "message": "Document processed successfully"})
        
    except Exception as e:
        print(f"Error processing upload: {e}")
        return JSONResponse(
            content={"status": "error", "message": str(e)},
            status_code=500
        )

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    try:
        await websocket.accept()
        
        # Send initial connection success message
        await websocket.send_text(json.dumps({
            "type": "status",
            "data": "Connected to server"
        }))
        
        # Use the global live_agent instance
        await live_agent.start_session(websocket)
        
    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        print(f"Error in websocket endpoint: {e}")
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "data": str(e)
            }))
        except:
            pass
        finally:
            await websocket.close()
