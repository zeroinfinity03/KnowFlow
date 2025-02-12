import aiohttp
from typing import AsyncGenerator
import json
import os
import sqlite3
import numpy as np
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

class LocalAgent:
    def __init__(self):
        # Ollama API endpoint (default local installation)
        self.api_url = "http://localhost:11434/api/generate"
        # Using Llama 3.2 3B - Meta's latest multilingual model optimized for:
        # - Following instructions
        # - Summarization
        # - Prompt rewriting
        # - Tool use
        # Supports: English, German, French, Italian, Portuguese, Hindi, Spanish, and Thai
        self.model = "llama3.2"
        
        # Initialize embedding model for semantic search
        self.embed_model = HuggingFaceEmbedding(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        
        # Initialize SQLite database
        self.db_path = "./data/conversations.db"
        os.makedirs("./data", exist_ok=True)
        self._init_db()
        
        # System prompt to improve formatting
        self.system_prompt = """You are a helpful AI assistant. Please format your responses clearly:
- Use proper markdown formatting
- Wrap code blocks with ```language_name
- Use bullet points and numbered lists appropriately
- Separate paragraphs with blank lines
- Use bold and italics for emphasis
"""

    def _init_db(self):
        """Initialize SQLite database with conversations table"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT,  -- 'user' or 'assistant'
                    message TEXT,
                    embedding BLOB,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Create index for faster retrieval
            conn.execute("CREATE INDEX IF NOT EXISTS idx_session ON conversations(session_id)")

    def _store_message(self, session_id: str, message: str, role: str):
        """Store message and its embedding in SQLite"""
        try:
            # Generate embedding
            embedding = self.embed_model.get_text_embedding(message)
            embedding_bytes = np.array(embedding).tobytes()
            
            # Store in database
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO conversations (session_id, role, message, embedding) VALUES (?, ?, ?, ?)",
                    (session_id, role, message, embedding_bytes)
                )
        except Exception as e:
            print(f"Error storing message: {e}")

    def _get_relevant_context(self, session_id: str, current_message: str, max_messages: int = 5):
        """Get most relevant previous messages using semantic search and chronological order"""
        try:
            # Get embedding for current message
            current_embedding = self.embed_model.get_text_embedding(current_message)
            
            with sqlite3.connect(self.db_path) as conn:
                # First, get the most recent messages in chronological order
                recent_messages = conn.execute(
                    """SELECT role, message, embedding, timestamp 
                       FROM conversations 
                       WHERE session_id = ?
                       ORDER BY timestamp DESC LIMIT 10""",
                    (session_id,)
                ).fetchall()
                
                if not recent_messages:
                    return ""
                
                # Calculate similarities and maintain chronological info
                messages_with_scores = []
                for role, message, embedding_bytes, timestamp in recent_messages:
                    embedding = np.frombuffer(embedding_bytes).reshape(-1)
                    similarity = np.dot(current_embedding, embedding) / (
                        np.linalg.norm(current_embedding) * np.linalg.norm(embedding)
                    )
                    messages_with_scores.append({
                        'role': role,
                        'message': message,
                        'similarity': similarity,
                        'timestamp': timestamp
                    })
                
                # Sort by similarity but maintain some chronological context
                # Include the last 2 messages regardless of similarity
                last_messages = messages_with_scores[:2]
                other_messages = sorted(
                    messages_with_scores[2:],
                    key=lambda x: x['similarity'],
                    reverse=True
                )[:max_messages-2]
                
                # Combine and sort by timestamp to maintain conversation flow
                selected_messages = last_messages + other_messages
                selected_messages.sort(key=lambda x: x['timestamp'])
                
                # Format messages
                formatted_messages = []
                for msg in selected_messages:
                    formatted_messages.append(f"{msg['role'].capitalize()}: {msg['message']}")
                
                return "\n".join(formatted_messages)
            
        except Exception as e:
            print(f"Error getting relevant context: {e}")
            return ""

    def _cleanup_old_sessions(self, hours: int = 24):
        """Remove conversations older than specified hours"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """DELETE FROM conversations 
                       WHERE timestamp < datetime('now', '-? hours')""",
                    (hours,)
                )
        except Exception as e:
            print(f"Error cleaning up old sessions: {e}")
        
    async def get_streaming_response(self, message: str, session_id: str) -> AsyncGenerator[str, None]:
        """
        Get streaming response from Ollama API using Llama 3.2 model.
        
        Args:
            message (str): User's input message
            session_id (str): Session identifier for context management
            
        Yields:
            str: Response chunks from the model
        """
        try:
            # Store user message
            self._store_message(session_id, message, "user")
            
            # Get relevant context
            context = self._get_relevant_context(session_id, message)
            
            # Prepare the request payload with system prompt and context
            prompt = f"{self.system_prompt}\n\n"
            if context:
                prompt += f"""Previous conversation:
{context}

Important: Only use the above context if it's directly relevant to the current question.
If the context is not relevant to the current question, ignore it and answer based on your knowledge.

"""
            prompt += f"User: {message}\nAssistant:"
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "top_k": 40
                }
            }
            
            current_response = ""
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, json=payload) as response:
                    # Read and process the streaming response
                    async for line in response.content:
                        if line:
                            try:
                                # Decode and parse the JSON response
                                chunk = json.loads(line.decode('utf-8'))
                                # Accumulate response and format
                                if chunk.get("response"):
                                    current_response += chunk["response"]
                                    # Only yield complete sentences or code blocks
                                    if any(char in current_response for char in ".!?\n```"):
                                        yield current_response
                                        current_response = ""
                            except json.JSONDecodeError:
                                continue
                    
                    # Yield any remaining response
                    if current_response:
                        yield current_response
                    
                    # Store assistant's complete response
                    self._store_message(session_id, current_response, "assistant")
                    
                    # Cleanup old sessions
                    self._cleanup_old_sessions()
                                
        except Exception as e:
            print(f"Error in LocalAgent streaming: {e}")
            yield f"Error: {str(e)}" 
