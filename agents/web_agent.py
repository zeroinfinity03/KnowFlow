import google.generativeai as genai
from typing import AsyncGenerator
import os
import aiohttp
import json
import ssl
import certifi

class WebAgent:
    def __init__(self):
        # Initialize Gemini
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
            
        # Initialize Tavily
        self.tavily_api_key = os.getenv("TAVILY_API_KEY")
        if not self.tavily_api_key:
            raise ValueError("TAVILY_API_KEY not found in environment variables")
            
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
    async def search_and_scrape(self, query: str, num_results: int = 5) -> list[str]:
        """
        Search using Tavily API - optimized for AI agents
        """
        # Tavily API endpoint
        url = "https://api.tavily.com/search"
        
        # Request parameters
        params = {
            "api_key": self.tavily_api_key,
            "query": query,
            "search_depth": "advanced",  # Get more comprehensive results
            "include_answer": True,      # Get a summarized answer
            "max_results": num_results,  # Number of results to return
        }
        
        print(f"\nSearching Tavily for: {query}")
        
        # First try with default SSL handling
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=params) as response:
                    return await self._process_tavily_response(response)
                    
        except (ssl.SSLError, aiohttp.ClientConnectorSSLError, aiohttp.ClientConnectorError) as ssl_error:
            # If we get an SSL error, retry with custom SSL context
            print(f"SSL error occurred: {str(ssl_error)}. Retrying with custom SSL context...")
            
            try:
                # Create an SSL context using certifi
                ssl_context = ssl.create_default_context(cafile=certifi.where())
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, json=params, ssl=ssl_context) as response:
                        return await self._process_tavily_response(response)
                        
            except Exception as e:
                print(f"Error during Tavily search with custom SSL context: {str(e)}")
                return []
                
        except Exception as e:
            print(f"Error during Tavily search: {str(e)}")
            return []
    
    async def _process_tavily_response(self, response):
        """Helper method to process the Tavily API response"""
        if response.status == 200:
            data = await response.json()
            
            results = []
            
            # Add Tavily's generated answer if available
            if "answer" in data and data["answer"]:
                results.append(f"Summary: {data['answer']}\n")
            
            # Process search results
            if "results" in data:
                for result in data["results"]:
                    title = result.get("title", "No title")
                    url = result.get("url", "No URL")
                    content = result.get("content", "No content")
                    
                    print(f"\nFound result: {title}")
                    print(f"URL: {url}")
                    
                    results.append(f"Source: {url}\nTitle: {title}\n\n{content}")
            
            return results
        else:
            error_data = await response.json()
            error_msg = f"Tavily API error: {error_data.get('error', 'Unknown error')}"
            print(error_msg)
            return []
            
    async def process_web_query(self, query: str) -> AsyncGenerator[str, None]:
        try:
            # Get search results from Tavily
            scraped_contents = await self.search_and_scrape(query)
            
            if not scraped_contents:
                yield "I couldn't find any relevant information for your query."
                return
            
            # Combine all scraped content
            combined_content = "\n\n---\n\n".join(scraped_contents)
            
            # Create a focused prompt for Gemini
            prompt = f"""Based on the following search results, please provide a comprehensive answer to: {query}
            
            Search Results:
            {combined_content}
            
            Please provide a detailed answer and include relevant source citations at the end of your response in a "Sources:" section. Format each source as a bullet point with the title and URL."""

            # Send to Gemini
            response = await self.model.generate_content_async(prompt, stream=True)
            
            async for chunk in response:
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            yield f"Error processing web query: {str(e)}"



