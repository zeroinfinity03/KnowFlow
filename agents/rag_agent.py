import os
from typing import Dict, List
import mimetypes
from llama_index.core.node_parser import TokenTextSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core import SimpleDirectoryReader, Document
import numpy as np
import chromadb
import uuid
import datetime
import aiohttp
import pytesseract
from PIL import Image
import io
import json

class RagAgent:
    def __init__(self):
        # Initialize embedding model
        self.embed_model = HuggingFaceEmbedding(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            cache_folder="./cache"
        )
        
        # Create data directory if it doesn't exist
        os.makedirs("./data/chroma", exist_ok=True)
        os.makedirs("./data/temp", exist_ok=True)  # For temporary file storage
        
        # Initialize ChromaDB with persistent storage
        self.chroma_client = chromadb.PersistentClient(path="./data/chroma")
        
        # Initialize text splitter
        self.text_splitter = TokenTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        
        # Ollama API endpoint (default local installation)
        self.ollama_api_url = "http://localhost:11434/api/generate"
        
        # Supported document types
        self.supported_mimes = {
            # Text Documents
            'application/pdf': '.pdf',
            'application/msword': '.doc',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
            'text/plain': '.txt',
            'text/markdown': '.md',
            'application/rtf': '.rtf',
            
            # Presentations
            'application/vnd.ms-powerpoint': '.ppt',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation': '.pptx',
            
            # Spreadsheets
            'application/vnd.ms-excel': '.xls',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
            'text/csv': '.csv',
            
            # Code
            'text/x-python': '.py',
            'application/javascript': '.js',
            'text/javascript': '.js',
            
            # Images
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'image/webp': '.webp',
            'image/tiff': '.tiff',
            'image/bmp': '.bmp'
        }

    def is_supported_file(self, file_content: bytes, filename: str) -> bool:
        """Check if the file type is supported."""
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type in self.supported_mimes if mime_type else False

    async def _process_image(self, file_content: bytes) -> str:
        """
        Process image using Tesseract OCR to extract text.
        
        Args:
            file_content (bytes): Raw image data
            
        Returns:
            str: Extracted text from the image
        """
        try:
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(file_content))
            
            # Convert image to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Extract text using Tesseract
            text = pytesseract.image_to_string(image)
            
            # Clean up extracted text
            text = text.strip()
            
            if not text:
                return "No text could be extracted from the image."
            
            return text
            
        except Exception as e:
            print(f"Error processing image with Tesseract: {str(e)}")
            raise

    async def process_document(self, file_content: bytes, filename: str, session_id: str) -> Dict:
        """
        Process a document or image and prepare it for RAG.
        
        Args:
            file_content (bytes): The binary content of the file
            filename (str): Original filename with extension
            session_id (str): Unique session identifier
            
        Returns:
            Dict: Processed document data ready for RAG
        """
        try:
            mime_type, _ = mimetypes.guess_type(filename)
            
            # Handle CSV files using DataFrame Agent
            if mime_type == 'text/csv':
                from .dataframe_agent import DataFrameAgent
                df_agent = DataFrameAgent()
                if await df_agent.load_dataframe(file_content, filename):
                    return {"status": "success", "message": "CSV file loaded successfully", "agent": "dataframe"}
                else:
                    raise Exception("Failed to load CSV file")
            
            # Handle images separately using Tesseract OCR
            if mime_type and mime_type.startswith('image/'):
                extracted_text = await self._process_image(file_content)
                document = Document(text=extracted_text, id_=filename)
                processed_data = await self._prepare_for_rag(document)
                await self._store_in_chroma(processed_data, session_id, filename)
                return {"status": "success", "message": "Image processed successfully"}
            
            # Handle other document types using LlamaIndex
            os.makedirs("./data/temp", exist_ok=True)
            temp_path = os.path.join("./data/temp", f"temp_{filename}")
            
            try:
                with open(temp_path, "wb") as f:
                    f.write(file_content)
                
                reader = SimpleDirectoryReader(
                    input_files=[temp_path],
                    filename_as_id=True
                )
                documents = reader.load_data()
                
                if not documents:
                    raise Exception("No content extracted from document")
                
                processed_data = await self._prepare_for_rag(documents[0])
                await self._store_in_chroma(processed_data, session_id, filename)
                
                return {"status": "success", "message": "Document processed successfully"}
                
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    
        except Exception as e:
            print(f"Error processing document: {str(e)}")
            raise

    async def _prepare_for_rag(self, document: Document) -> Dict:
        """
        Prepare document for RAG processing.
        - Takes LlamaIndex Document
        - Chunks the text while preserving context
        - Generates embeddings for chunks
        - Maintains metadata
        """
        try:
            # Extract text and metadata from LlamaIndex Document
            content = document.text
            metadata = {
                "file_type": mimetypes.guess_type(document.id_)[0],
                "filename": document.id_,
                "parse_timestamp": str(datetime.datetime.now())
            }
            
            # Create chunks using the text splitter
            chunks = self.text_splitter.split_text(content)
            
            # Generate embeddings for chunks
            embeddings = await self._generate_embeddings(chunks)
            
            # Prepare processed data
            processed_data = {
                'chunks': chunks,
                'embeddings': embeddings,
                'metadata': metadata,
                'total_chunks': len(chunks)
            }
            
            return processed_data
                
        except Exception as e:
            print(f"Error in _prepare_for_rag: {str(e)}")
            raise

    async def _generate_embeddings(self, chunks: List[str]) -> List[np.ndarray]:
        """
        Generate embeddings for text chunks using HuggingFace model.
        Uses batch processing for better performance.
        
        Args:
            chunks: List of text chunks to generate embeddings for
            
        Returns:
            List of numpy arrays containing embeddings
        """
        try:
            # Process chunks in batches for better performance
            batch_size = 32
            embeddings = []
            
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]
                try:
                    # Generate embeddings for the batch
                    batch_embeddings = [
                        self.embed_model.get_text_embedding(
                            text=chunk,
                        ) for chunk in batch
                    ]
                    embeddings.extend(batch_embeddings)
                except Exception as batch_error:
                    print(f"Error processing batch {i//batch_size}: {batch_error}")
                    # If a batch fails, process chunks individually as fallback
                    for chunk in batch:
                        try:
                            embedding = self.embed_model.get_text_embedding(
                                text=chunk,
                            )
                            embeddings.append(embedding)
                        except Exception as chunk_error:
                            print(f"Error processing chunk: {chunk_error}")
                            # Add a zero vector as placeholder for failed chunks
                            embeddings.append(np.zeros(384))  # all-MiniLM-L6-v2 dimension is 384
            
            if not embeddings:
                raise Exception("No embeddings could be generated")
                
            return embeddings
            
        except Exception as e:
            print(f"Error in embedding generation: {str(e)}")
            raise

    def get_supported_extensions(self) -> List[str]:
        """Get list of supported file extensions."""
        return list(set(self.supported_mimes.values()))

    async def _store_in_chroma(self, processed_data: Dict, session_id: str, filename: str):
        """Store processed document data in ChromaDB with persistent collections."""
        try:
            # Create a sanitized collection name based on the filename
            # Replace spaces and special characters, ensure it meets ChromaDB requirements
            sanitized_name = (
                filename.lower()                    # First convert to lowercase
                .replace(" ", "_")                 # Replace spaces with underscores
                .replace(".", "_")                # Replace periods with underscores
                .replace("(", "")                 # Remove parentheses
                .replace(")", "")
                .replace("-", "_")                # Replace hyphens with underscores
                .replace("@", "")                 # Remove @ symbol
                .replace("#", "")                 # Remove # symbol
                .replace("&", "")                 # Remove & symbol
                .replace("+", "")                 # Remove + symbol
            )
            
            # Remove any consecutive underscores
            while "__" in sanitized_name:
                sanitized_name = sanitized_name.replace("__", "_")
            
            # Remove any non-alphanumeric characters (except underscores)
            sanitized_name = "".join(c for c in sanitized_name if c.isalnum() or c == "_")
            
            # Ensure the name starts with a letter
            if not sanitized_name[0].isalpha():
                sanitized_name = "doc_" + sanitized_name
            
            # Ensure the name ends with an alphanumeric character
            if not sanitized_name[-1].isalnum():
                sanitized_name = sanitized_name[:-1]
            
            # Limit length to comply with ChromaDB's 63-character limit
            if len(sanitized_name) > 63:
                sanitized_name = sanitized_name[:63]
                # Ensure it still ends with an alphanumeric character
                while not sanitized_name[-1].isalnum():
                    sanitized_name = sanitized_name[:-1]
            
            collection_name = f"collection_{sanitized_name}"
            
            print(f"Using collection name: {collection_name}")  # Debug print
            
            # Get or create collection
            collection = None
            try:
                # Try to get existing collection
                collection = self.chroma_client.get_collection(name=collection_name)
                print(f"Updating existing collection: {collection_name}")
            except Exception:
                # Collection doesn't exist, create new one
                print(f"Creating new collection: {collection_name}")
                collection = self.chroma_client.create_collection(
                    name=collection_name,
                    metadata={
                        "filename": filename,
                        "last_updated": str(datetime.datetime.now())
                    }
                )
            
            # Clear existing entries if collection exists
            if collection.count() > 0:
                collection.delete(
                    where={"source": {"$eq": filename}}  # Delete entries matching this filename
                )
            
            # Generate unique IDs for chunks
            chunk_ids = [str(uuid.uuid4()) for _ in processed_data['chunks']]
            
            # Clean and validate metadata
            def clean_metadata_value(value):
                if value is None:
                    return ""  # Convert None to empty string
                if isinstance(value, (str, int, float, bool)):
                    return value
                return str(value)  # Convert other types to string
            
            base_metadata = {
                k: clean_metadata_value(v)
                for k, v in processed_data['metadata'].items()
            }
            
            # Prepare metadata for each chunk
            metadatas = [{
                "chunk_index": idx,
                "source": filename,
                **base_metadata
            } for idx in range(len(processed_data['chunks']))]
            
            # Add data to collection
            collection.add(
                ids=chunk_ids,
                embeddings=processed_data['embeddings'],
                documents=processed_data['chunks'],
                metadatas=metadatas
            )
            
            # Store the current collection name in the session metadata
            session_collection = self.chroma_client.get_or_create_collection(
                name="session_metadata",
                metadata={"description": "Stores session to document mappings"}
            )
            
            # Update session to collection mapping
            session_collection.upsert(
                ids=[session_id],
                documents=[collection_name],
                metadatas=[{
                    "filename": filename,
                    "timestamp": str(datetime.datetime.now())
                }],
                embeddings=[[0] * 384]  # Dummy embedding as it's not used for lookups
            )
            
            print(f"Successfully processed and stored document: {filename}")
            
        except Exception as e:
            print(f"Error storing in ChromaDB: {str(e)}")
            raise

    async def get_relevant_context(self, query: str, session_id: str, n_results: int = 3) -> List[str]:
        """Get relevant document chunks for a query using the session's associated document."""
        try:
            # Get the collection name for this session
            session_collection = self.chroma_client.get_collection(name="session_metadata")
            results = session_collection.get(
                ids=[session_id],
                include=['documents', 'metadatas']
            )
            
            if not results['documents']:
                return []
                
            collection_name = results['documents'][0]
            
            # Get the actual document collection
            collection = self.chroma_client.get_collection(name=collection_name)
            
            # Generate embedding for query
            query_embedding = self.embed_model.get_text_embedding(query)
            
            # Query collection
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )
            
            # Return relevant chunks
            return results['documents'][0] if results['documents'] else []
            
        except Exception as e:
            print(f"Error getting relevant context: {str(e)}")
            # If session or collection not found, return empty list
            return []

    def _cleanup_old_collections(self, days: int = 30):
        """Clean up document collections older than specified days."""
        try:
            collections = self.chroma_client.list_collections()
            current_time = datetime.datetime.now()
            
            for collection in collections:
                if collection.name.startswith("document_"):
                    metadata = collection.metadata
                    if metadata and "last_updated" in metadata:
                        last_updated = datetime.datetime.fromisoformat(metadata["last_updated"])
                        if (current_time - last_updated).days > days:
                            self.chroma_client.delete_collection(collection.name)
                            print(f"Deleted old collection: {collection.name}")
                            
        except Exception as e:
            print(f"Error cleaning up old collections: {str(e)}")

    async def _generate_answer(self, prompt: str) -> str:
        """Generate answer using local Ollama model."""
        try:
            # Using Llama 3.2 3B model - Meta's latest multilingual model optimized for:
            # - Following instructions
            # - Summarization
            # - Prompt rewriting
            # - Tool use
            payload = {
                "model": "llama3.2",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "top_k": 40  # Added to match LocalAgent settings
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.ollama_api_url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("response", "")
                    else:
                        raise Exception(f"Error from Ollama API: {response.status}")
                        
        except Exception as e:
            print(f"Error generating answer: {e}")
            raise

    async def answer_question(self, question: str, session_id: str) -> str:
        """
        Answer a question using RAG with local LLM.
        
        Args:
            question (str): User's question
            session_id (str): Session identifier
            
        Returns:
            str: Generated answer based on document context
        """
        try:
            # Get relevant context
            context_chunks = await self.get_relevant_context(question, session_id)
            
            if not context_chunks:
                return "I don't have enough context to answer that question. Please make sure a document is uploaded first."
            
            # Combine context chunks
            context = "\n\n".join(context_chunks)
            
            # Create prompt for local model
            prompt = f"""Using ONLY the following context, answer the question.
            If the answer cannot be found in the context, say so clearly.
            
            Context:
            {context}
            
            Question: {question}
            
            Answer: """
            
            # Generate answer using local LLM
            answer = await self._generate_answer(prompt)
            
            # Return answer with local LLM flag
            return json.dumps({
                "chunk": answer,
                "is_local_llm": True
            })
            
        except Exception as e:
            print(f"Error answering question: {str(e)}")
            raise
