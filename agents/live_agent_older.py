import os
import json
import asyncio
import websockets
from google import genai
import base64
from dotenv import load_dotenv

class LiveAgent:
    def __init__(self):
        load_dotenv()
        
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set")
            
        # Initialize Gemini client
        self.client = genai.Client(
            api_key=api_key,
            http_options={'api_version': 'v1alpha'}
        )
        self.model = "models/gemini-2.0-flash-exp"

    async def send_to_gemini(self, client_websocket, session):
        """Sends messages from the client websocket to the Gemini API."""
        try:
            while True:
                try:
                    message = await client_websocket.receive_text()
                    data = json.loads(message)
                    
                    if "realtime_input" in data:
                        for chunk in data["realtime_input"]["media_chunks"]:
                            if chunk["mime_type"] == "audio/pcm":
                                await session.send(input={"mime_type": "audio/pcm", "data": chunk["data"]})
                            elif chunk["mime_type"] == "image/jpeg":
                                await session.send(input={"mime_type": "image/jpeg", "data": chunk["data"]})
                            
                except websockets.exceptions.ConnectionClosed:
                    print("Client connection closed")
                    break
                except Exception as e:
                    print(f"Error sending to Gemini: {e}")
                    continue
        except Exception as e:
            print(f"Error in send_to_gemini: {e}")
        finally:
            print("send_to_gemini closed")

    async def receive_from_gemini(self, client_websocket, session):
        """Receives responses from the Gemini API and forwards them to the client."""
        try:
            while True:
                try:
                    print("receiving from gemini")
                    async for response in session.receive():
                        print(f"response: {response}")
                        if response.server_content is None:
                            print(f'Unhandled server message! - {response}')
                            continue

                        model_turn = response.server_content.model_turn
                        if model_turn:
                            for part in model_turn.parts:
                                print(f"part: {part}")
                                if hasattr(part, 'text') and part.text is not None:
                                    await client_websocket.send_text(json.dumps({"text": part.text}))
                                elif hasattr(part, 'inline_data') and part.inline_data is not None:
                                    print("Processing audio response")
                                    print("Audio mime_type:", part.inline_data.mime_type)
                                    base64_audio = base64.b64encode(part.inline_data.data).decode('utf-8')
                                    await client_websocket.send_text(json.dumps({
                                        "audio": base64_audio
                                    }))
                                    print("Audio sent to client")

                        if response.server_content.turn_complete:
                            print('\n<Turn complete>')

                except websockets.exceptions.ConnectionClosed:
                    print("Client connection closed normally (receive)")
                    break
                except Exception as e:
                    print(f"Error receiving from Gemini: {e}")
                    break

        except Exception as e:
            print(f"Error in receive_from_gemini: {e}")
        finally:
            print("Gemini connection closed (receive)")

    async def start_session(self, websocket):
        """Start a streaming session with Gemini."""
        try:
            # Get initial config using receive_text()
            config_message = await websocket.receive_text()
            config_data = json.loads(config_message)
            config = config_data.get("setup", {})

            async with self.client.aio.live.connect(model=self.model, config=config) as session:
                print("Connected to Gemini API")

                # Create tasks for sending and receiving
                send_task = asyncio.create_task(self.send_to_gemini(websocket, session))
                receive_task = asyncio.create_task(self.receive_from_gemini(websocket, session))
                
                # Wait for both tasks
                await asyncio.gather(send_task, receive_task)

        except Exception as e:
            print(f"Error in Gemini session: {e}")
        finally:
            print("Gemini session closed")
