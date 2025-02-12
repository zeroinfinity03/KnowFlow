import google.generativeai as genai
from typing import Optional, AsyncGenerator
import os
from pydantic import BaseModel

class ChatResponse(BaseModel):
    response: str

class TextAgent:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        genai.configure(api_key=api_key)
        # Initialize with correct model name
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        # Initialize chat history
        self.chat = self.model.start_chat(history=[])
        
    async def get_streaming_response(self, message: str) -> AsyncGenerator[str, None]:
        try:
            # Send message using the chat session to maintain context
            response = await self.chat.send_message_async(
                message,
                stream=True  # Enable streaming
            )
            
            async for chunk in response:
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            print(f"Error in TextAgent streaming: {e}")
            yield f"Error: {str(e)}"
