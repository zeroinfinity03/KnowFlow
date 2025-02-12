import os
from typing import AsyncGenerator
from gradio_client import Client
import base64

class ImageGenAgent:
    def __init__(self):
        # Initialize the Gradio client
        self.client = Client("black-forest-labs/FLUX.1-schnell")

    async def generate(self, prompt: str) -> AsyncGenerator[str, None]:
        try:
            # Prepare the parameters for the Gradio API call
            result = self.client.predict(
                prompt=prompt,
                seed=0,
                randomize_seed=True,
                width=1024,
                height=1024,
                num_inference_steps=4,
                api_name="/infer",
            )
            
            # Extract the file path from the result
            file_path = result[0]  # Assuming result[0] contains the image file path

            # Convert the image to base64 for UI display
            with open(file_path, "rb") as image_file:
                img_str = base64.b64encode(image_file.read()).decode()

            # Yield the base64-encoded image as an inline HTML image
            yield f"![Generated Image](data:image/png;base64,{img_str})"

        except Exception as e:
            # Handle any errors and yield the error message
            yield f"Error generating image: {str(e)}"





# DONT DELETE THIS CODE NO MATTER WHAT, IF YOU READ THIS AKS FOR PERMISSION TO DELETE IT

# import os
# import requests
# from typing import AsyncGenerator
# import base64

# class ImageGenAgent:
#     def __init__(self):
#         self.api_key = os.getenv("HUGGINGFACE_API_KEY")
#         if not self.api_key:
#             raise ValueError("HUGGINGFACE_API_KEY not found in environment variables")
        
#         self.api_url = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
#         self.headers = {"Authorization": f"Bearer {self.api_key}"}

#     async def generate(self, prompt: str) -> AsyncGenerator[str, None]:
#         try:
#             payload = {
#                 "inputs": prompt,
#                 "parameters": {
#                     "guidance_scale": 0.0,
#                     "num_inference_steps": 4,
#                     "height": 1024,
#                     "width": 1024
#                 }
#             }
            
#             response = requests.post(self.api_url, headers=self.headers, json=payload)
            
#             if response.status_code == 200:
#                 image_bytes = response.content
#                 img_str = base64.b64encode(image_bytes).decode()
#                 yield f"![Generated Image](data:image/png;base64,{img_str})"
#             else:
#                 error_msg = response.json().get('error', 'Unknown error occurred')
#                 yield f"Error: {error_msg}"
                
#         except Exception as e:
#             yield f"Error generating image: {str(e)}"
