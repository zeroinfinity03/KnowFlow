import google.generativeai as genai
import base64
import os
from typing import AsyncGenerator
import json
from dotenv import load_dotenv
from google.cloud import texttospeech
import pathlib

# Load environment variables first
load_dotenv()

# Get and validate the credentials path
credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
if not credentials_path:
    raise ValueError("GOOGLE_APPLICATION_CREDENTIALS not found in .env file")

# Convert relative path to absolute if needed
if not os.path.isabs(credentials_path):
    base_dir = pathlib.Path(__file__).parent.parent
    credentials_path = os.path.join(base_dir, credentials_path)

# Verify the credentials file exists
if not os.path.exists(credentials_path):
    raise ValueError(f"Google Cloud credentials file not found at: {credentials_path}")

# Set the environment variable with the absolute path
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

DEFAULT_PROMPT = """
You are a helpful AI assistant. When you receive audio and an image:
1. Focus on answering the question asked in the audio in the same language.
2. If the question is asked in Hindi, reply in Hindi. If in Spanish, reply in Spanish.
3. Only describe the image if the question is about the image, I repeat if no queesion is asked in the audio then dont say anything.
4. Don't describe that you received an audio or image input.
5. If the question is about a particular product analyze first what is that product actually by reading the label etc then answer about that product from your knowledgebase.
6. At the end of your response, add: "Question asked in: [language]"

Example 1:
If audio asks: "How many calories in this chocolate?"
Bad response: "The audio contains someone asking about calories. The image shows a chocolate bar..."
Good response: "This Ghirardelli 86% dark chocolate bar contains 190 calories per serving (40g).
Question asked in: English"

Example 2:
If audio asks: "इस चॉकलेट में कितनी कैलोरी हैं?"
Good response: "यह Ghirardelli 86% डार्क चॉकलेट बार प्रति सर्विंग (34 ग्राम) में 190 कैलोरी प्रदान करता है।
Bad response: "This Ghirardelli 86% dark chocolate bar contains 190 calories per serving (40g).
Question asked in: Hindi"
"""


class ObjectDetectionAgent:
    def __init__(self):
        # Initialize Gemini
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Initialize Google Cloud TTS
        try:
            # Credentials are already set up at module level
            self.tts_client = texttospeech.TextToSpeechClient()
        except Exception as e:
            print(f"Error initializing TTS client: {str(e)}")
            raise
        
    def synthesize_speech(self, text: str, language: str) -> str:
        # Map of language codes to single appropriate Wavenet voice
        language_voices = {
            'english': ('en-US', 'en-US-Wavenet-D'),
            'hindi': ('hi-IN', 'hi-IN-Wavenet-A'),
            'spanish': ('es-ES', 'es-ES-Wavenet-B'),
            'french': ('fr-FR', 'fr-FR-Wavenet-C'),
            'german': ('de-DE', 'de-DE-Wavenet-F'),
            'japanese': ('ja-JP', 'ja-JP-Wavenet-B'),
            'korean': ('ko-KR', 'ko-KR-Wavenet-A'),
            'chinese': ('cmn-CN', 'cmn-CN-Wavenet-A')
        }
        
        # Default to English if language not supported
        language_code, voice_name = language_voices.get(language.lower(), ('en-US', 'en-US-Wavenet-D'))
        
        try:
            input_text = texttospeech.SynthesisInput(text=text)
            
            voice = texttospeech.VoiceSelectionParams(
                language_code=language_code,
                name=voice_name
            )
            
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            )
            
            response = self.tts_client.synthesize_speech(
                input=input_text,
                voice=voice,
                audio_config=audio_config
            )
            
            return base64.b64encode(response.audio_content).decode('utf-8')
            
        except Exception as e:
            print(f"Error with voice {voice_name}: {str(e)}")
            # Fallback to Standard voice if Wavenet fails
            try:
                voice = texttospeech.VoiceSelectionParams(
                    language_code=language_code,
                    name=f"{language_code}-Standard-A"
                )
                
                response = self.tts_client.synthesize_speech(
                    input=input_text,
                    voice=voice,
                    audio_config=audio_config
                )
                
                return base64.b64encode(response.audio_content).decode('utf-8')
            except Exception as e:
                print(f"Error with fallback voice: {str(e)}")
                raise
        
    async def process_input(self, audio_base64: str, image_base64: str) -> AsyncGenerator[str, None]:
        try:
            # Create multimodal content
            contents = [
                {
                    "parts": [
                        {"text": DEFAULT_PROMPT},
                        {
                            "inline_data": {
                                "mime_type": "audio/webm",
                                "data": audio_base64
                            }
                        },
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": image_base64
                            }
                        }
                    ]
                }
            ]
            
            # Get response from Gemini
            response = await self.model.generate_content_async(
                contents,
                stream=True,
                generation_config={
                    "temperature": 0.7,
                    "top_p": 0.8,
                    "top_k": 40
                }
            )
            
            full_response = ""
            async for chunk in response:
                if chunk.text:
                    full_response += chunk.text
            
            # Extract language and remove it from response text
            parts = full_response.rsplit("Question asked in:", 1)
            text_response = parts[0].strip()
            language = parts[1].strip() if len(parts) > 1 else "English"
            
            # Convert to speech
            audio_content = self.synthesize_speech(text_response, language)
            
            # Return audio content
            yield json.dumps({
                "audio": audio_content,
                "language": language
            })
                    
        except Exception as e:
            error_msg = f"Error in ObjectDetectionAgent: {str(e)}"
            print(error_msg)
            yield error_msg


