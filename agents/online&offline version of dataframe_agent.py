# If you need to use online which is faster version copy & paste it in the dataframe_agent.py


from langchain_ollama import OllamaLLM
import pandas as pd
import io
import logging
import json
import asyncio
import re
from typing import AsyncGenerator, Dict, Any, Optional, List
import numpy as np
import os
import sys
from dotenv import load_dotenv
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI

# Import plotly express with error handling
try:
    import plotly.express as px
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("Could not import plotly express. Visualizations will be disabled.")
    px = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataFrameAgent:
    """Async DataFrameAgent for analyzing pandas DataFrames with LLMs"""
    
    def __init__(self):
        """Initialize the DataFrame agent"""
        # Load environment variables
        load_dotenv()
        self.google_api_key = os.getenv("GEMINI_API_KEY")
        if not self.google_api_key:
            logger.warning("GEMINI_API_KEY not found in environment variables. Please set it to use Gemini.")
        
        # Initialize other properties
        self.llm = None
        self.df = None
        self.dataset_details = None
        self._plotly_available = self._check_plotly_available()
        
    def _check_plotly_available(self) -> bool:
        """Check if plotly is available for visualizations"""
        try:
            import plotly.express
            return True
        except ImportError:
            logger.warning("Plotly express is not available. Visualizations will be disabled.")
            return False
    
    async def load_dataframe(self, file_content: bytes, filename: str = "data.csv") -> bool:
        """
        Load a CSV file into a pandas DataFrame and initialize the LLM.
        
        Args:
            file_content: The binary content of the CSV file
            filename: The name of the uploaded file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Load CSV into pandas DataFrame
            self.df = pd.read_csv(io.BytesIO(file_content))
            logger.info(f"Loaded {filename} | Shape: {self.df.shape}")
            
            # Initialize Gemini LLM
            if self.google_api_key:
                self.llm = ChatGoogleGenerativeAI(
                    model="gemini-2.0-flash-exp",
                    temperature=0.0,
                    google_api_key=self.google_api_key,
                )
                logger.info("Google Gemini LLM initialized")
            else:
                # Fallback to Ollama if Google API key is not available
                self.llm = OllamaLLM(model="llama3.2", temperature=0.1)
                logger.info("Ollama LLM initialized (fallback)")
            
            # Automatically run basic analysis commands
            self.dataset_details = self._collect_dataset_details()
            logger.info("Collected dataset details")
            
            return True
        except Exception as e:
            logger.error(f"Error loading CSV file: {str(e)}")
            return False
    
    def _collect_dataset_details(self) -> str:
        """
        Collect basic dataset details using df.info().
        
        Returns:
            A string containing the dataset details from df.info()
        """
        if self.df is None:
            return "No DataFrame loaded"
        
        details = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = details
        
        try:
            print("=== DATASET OVERVIEW ===")
            print(f"\nDataset Shape: {self.df.shape}")
            print(f"\nColumn Names: {list(self.df.columns)}")
            print("\nDataset Information:")
            self.df.info(verbose=True)
            print("\nSample Data (first 5 rows):")
            print(self.df.head(5))
            print("\nStatistical Summary:")
            print(self.df.describe())
            
            return details.getvalue()
        finally:
            sys.stdout = old_stdout
    
    async def analyze(self, query: str, timeout: int = 60) -> AsyncGenerator[str, None]:
        """
        Process a user query about the DataFrame and yield results.
        
        Args:
            query: The user's question about the DataFrame
            timeout: Maximum time in seconds to wait for a response
            
        Yields:
            JSON strings containing response chunks
        """
        if not hasattr(self, 'df') or self.df is None:
            yield json.dumps({"chunk": "No DataFrame loaded. Please upload a CSV file first."})
            return
        
        # Make sure plotly express is available at the module level
        global px
        if 'px' not in globals():
            import plotly.express as px
        
        # Handle basic dataset description questions
        describe_pattern = re.compile(r'(describe|summarize|tell me about|what\'s in|show me|explain) (the|this) (data|dataset|table|dataframe)', re.IGNORECASE)
        if describe_pattern.search(query):
            # Create a visualization of column counts
            try:
                # Generate a basic overview visualization
                fig = None
                visualization_html = None
                
                # Only attempt visualization if plotly is available
                if self._plotly_available:
                    # Use plotly to create a column data types visualization
                    column_types = self.df.dtypes.astype(str).value_counts()
                    if len(column_types) > 0:
                        try:
                            import plotly.express as px
                            fig = px.pie(
                                values=column_types.values, 
                                names=column_types.index, 
                                title="Column Data Types Distribution"
                            )
                            visualization_html = fig.to_html(full_html=False, include_plotlyjs='cdn')
                        except Exception as viz_error:
                            logger.error(f"Error creating visualization: {str(viz_error)}")
                
                # Provide basic description from our collected dataset details
                description = f"This dataset has {self.df.shape[0]} rows and {self.df.shape[1]} columns.\n\n"
                description += f"The columns are: {', '.join(self.df.columns)}\n\n"
                description += f"Here's a sample of the data (first 5 rows):\n{self.df.head(5).to_string()}"
                
                # Return response with or without visualization
                if visualization_html:
                    yield json.dumps({
                        "chunk": description,
                        "visualization": visualization_html,
                        "is_local_llm": True
                    })
                else:
                    yield json.dumps({
                        "chunk": description,
                        "is_local_llm": True
                    })
                
            except Exception as e:
                logger.error(f"Error generating dataset overview: {str(e)}")
                # Fallback to basic text description
                description = f"This dataset has {self.df.shape[0]} rows and {self.df.shape[1]} columns.\n\n"
                description += f"The columns are: {', '.join(self.df.columns)}"
                
                yield json.dumps({
                    "chunk": description,
                    "is_local_llm": True
                })
            
            return
        
        try:
            # Create a prompt that matches the Streamlit implementation
            message = f"""You are a data analysis assistant. You have access to a DataFrame named 'df'. When analyzing this DataFrame, follow these rules:

1. For calculations:
   - NEVER create sample data or new DataFrames
   - ALWAYS use the existing 'df' DataFrame
   - Use Python code to calculate exact values
   - Print results with print()
   - DO NOT modify calculated values

2. For visualizations:
   - Use plotly.express as px
   - Always save plots to a variable named 'fig'
   - Create beautiful and professional visualizations
   - Include clear titles and labels
   - For count plots, sort the data chronologically
   - Use color='Count' for gradient effects in bar plots

Example for counting and plotting:
Thought: I need to create a count plot by Model Year
Action: python_repl_ast
Action Input: 
import plotly.express as px

# Get value counts and create plot
counts = df['Model Year'].value_counts().reset_index()
counts.columns = ['Model Year', 'Count']
counts = counts.sort_values('Model Year')  # Sort chronologically

# Create beautiful visualization with gradient
fig = px.bar(counts, 
             x='Model Year', 
             y='Count',
             color='Count',  # This creates a gradient based on count values
             title='Vehicle Distribution by Model Year',
             labels={{'Model Year': 'Model Year', 'Count': 'Number of Vehicles'}})

# Enhance the layout
fig.update_layout(
    template="plotly_white",
    bargap=0.2,
    plot_bgcolor="white",
    paper_bgcolor="white",
    showlegend=False,
    coloraxis_showscale=False  # Hide color scale
)

THE DATASET DETAILS:
{self.dataset_details}

USER QUESTION: 
{query}

Format your response with code wrapped in ```python and ``` markers.
"""
            
            # Get response from LLM with timeout
            response_future = asyncio.create_task(self.llm.ainvoke(message))
            response = await asyncio.wait_for(response_future, timeout)
            
            # Extract the content from AIMessage if needed
            if hasattr(response, 'content'):
                response_text = response.content
            else:
                response_text = str(response)
            
            # Extract Python code from the response
            code_pattern = r"```python\s*(.*?)\s*```"
            code_match = re.search(code_pattern, response_text, re.DOTALL)
            
            if not code_match:
                yield json.dumps({
                    "chunk": f"I couldn't generate code to answer your question. Please try rephrasing your query.",
                    "is_local_llm": True
                })
                return
            
            # Get the code and log it
            code = code_match.group(1).strip()
            logger.info(f"Generated code: {code}")
            
            # Create a safe execution environment with all required imports
            local_vars = {
                "df": self.df.copy(), 
                "np": np, 
                "pd": pd
            }
            
            # Ensure px is imported and available in local_vars if plotly is available
            if self._plotly_available:
                try:
                    import plotly.express as px
                    local_vars["px"] = px
                    # Add enhanced plotly configuration
                    import plotly.io as pio
                    pio.templates.default = "plotly_white"  # Set default template
                    local_vars["pio"] = pio
                except ImportError:
                    logger.warning("Could not import plotly express (px). Visualizations will not be available.")
            
            # Capture stdout to get printed output
            old_stdout = sys.stdout
            mystdout = io.StringIO()
            sys.stdout = mystdout
            
            # Execute the code
            try:
                # Ensure df is in both globals and locals for exec
                globals_dict = globals().copy()
                globals_dict["df"] = self.df.copy()
                
                exec(code, globals_dict, local_vars)
                output = mystdout.getvalue()
                
                # Check if a plotly figure was created
                fig = None
                has_visualization = False
                for var_name, var_value in local_vars.items():
                    if var_name == 'fig' and 'plotly' in str(type(var_value)):
                        fig = var_value
                        has_visualization = True
                        break
                
                # Capture visualization HTML if present
                visualization_html = None
                if fig:
                    try:
                        visualization_html = fig.to_html(full_html=False, include_plotlyjs='cdn')
                    except Exception as viz_error:
                        logger.error(f"Error creating visualization HTML: {str(viz_error)}")
                
                # Send the output directly to the LLM with a simple prompt
                interpretation_message = f"""Give a clear, direct answer to the user's question: "{query}"

Based on the analysis results:
{output}

Keep your answer concise and focused on the key insights from the data. Speak in first person as if you did the analysis yourself."""
                
                # If there's a visualization, add a note about it
                if has_visualization:
                    interpretation_message += """

Note: I've created a visualization to better illustrate these insights."""
                
                # Get LLM's interpretation of the results
                interpretation = await self.llm.ainvoke(interpretation_message)
                
                # Extract content from AIMessage if needed
                if hasattr(interpretation, 'content'):
                    interpretation_text = interpretation.content
                else:
                    interpretation_text = str(interpretation)
                
                # Format the final result with only the LLM's interpretation (and visualization if present)
                if visualization_html:
                    # Use a special JSON structure to separate text content from visualization
                    # This will allow the frontend to properly render the visualization
                    response_json = json.dumps({
                        "chunk": interpretation_text,
                        "visualization": visualization_html,
                        "is_local_llm": True
                    })
                else:
                    response_json = json.dumps({
                        "chunk": interpretation_text,
                        "is_local_llm": True
                    })
                
                yield response_json
                
            except Exception as e:
                error_msg = f"Error executing code: {str(e)}"
                logger.error(error_msg)
                
                # Provide a more user-friendly error message through the LLM
                error_message = f"""You are a helpful data analysis assistant. 

A user asked this question about a dataset: "{query}"

When trying to analyze the data, this error occurred: "{str(e)}"

Provide a brief, simple explanation of what might have gone wrong and suggest alternatives
or a better way to ask the question. Be helpful and concise."""
                
                try:
                    # Get a user-friendly explanation of the error
                    error_explanation = await self.llm.ainvoke(error_message)
                    
                    # Extract content from AIMessage if needed
                    if hasattr(error_explanation, 'content'):
                        error_explanation_text = error_explanation.content
                    else:
                        error_explanation_text = str(error_explanation)
                    
                    yield json.dumps({
                        "chunk": error_explanation_text,
                        "is_local_llm": True
                    })
                except Exception:
                    # Fallback to simple error message if LLM fails
                    yield json.dumps({
                        "chunk": f"Error: {error_msg}. Please try rephrasing your question or checking if the data contains the information you're looking for.",
                        "is_local_llm": True
                    })
            finally:
                # Restore stdout
                sys.stdout = old_stdout
                
        except asyncio.TimeoutError:
            logger.warning(f"Query timed out after {timeout} seconds: {query[:100]}...")
            yield json.dumps({
                "chunk": f"Analysis timed out after {timeout} seconds. Please try a simpler query or increase the timeout limit.",
                "is_local_llm": True
            })
        except Exception as e:
            error_msg = f"Error processing query: {str(e)}"
            logger.error(error_msg)
            yield json.dumps({
                "chunk": f"Error during analysis: {error_msg}",
                "is_local_llm": True
            })















# If you need to use offline which uses local llm  but its little slower, So use this code,  just copy & paste it in the dataframe_agent.py


from langchain_ollama import OllamaLLM
import pandas as pd
import io
import logging
import json
import asyncio
import re
from typing import AsyncGenerator, Dict, Any, Optional, List
import numpy as np
import os
import sys
from dotenv import load_dotenv

# Import plotly express with error handling
try:
    import plotly.express as px
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("Could not import plotly express. Visualizations will be disabled.")
    px = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataFrameAgent:
    """Async DataFrameAgent for analyzing pandas DataFrames with LLMs"""
    
    def __init__(self):
        """Initialize the DataFrame agent"""
        # Load environment variables
        load_dotenv()
        
        # Initialize other properties
        self.llm = None
        self.df = None
        self.dataset_details = None
        self._plotly_available = self._check_plotly_available()
        
    def _check_plotly_available(self) -> bool:
        """Check if plotly is available for visualizations"""
        try:
            import plotly.express
            return True
        except ImportError:
            logger.warning("Plotly express is not available. Visualizations will be disabled.")
            return False
    
    async def load_dataframe(self, file_content: bytes, filename: str = "data.csv") -> bool:
        """
        Load a CSV file into a pandas DataFrame and initialize the LLM.
        
        Args:
            file_content: The binary content of the CSV file
            filename: The name of the uploaded file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Load CSV into pandas DataFrame
            self.df = pd.read_csv(io.BytesIO(file_content))
            logger.info(f"Loaded {filename} | Shape: {self.df.shape}")
            
            # Initialize Ollama LLM - no fallback, only use llama3.2
            self.llm = OllamaLLM(model="llama3.2", temperature=0.1)
            logger.info("Ollama LLM initialized")
            
            # Automatically run basic analysis commands
            self.dataset_details = self._collect_dataset_details()
            logger.info("Collected dataset details")
            
            return True
        except Exception as e:
            logger.error(f"Error loading CSV file: {str(e)}")
            return False
    
    def _collect_dataset_details(self) -> str:
        """
        Collect basic dataset details using df.info().
        
        Returns:
            A string containing the dataset details from df.info()
        """
        if self.df is None:
            return "No DataFrame loaded"
        
        details = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = details
        
        try:
            print("=== DATASET OVERVIEW ===")
            print(f"\nDataset Shape: {self.df.shape}")
            print(f"\nColumn Names: {list(self.df.columns)}")
            print("\nDataset Information:")
            self.df.info(verbose=True)
            print("\nSample Data (first 5 rows):")
            print(self.df.head(5))
            print("\nStatistical Summary:")
            print(self.df.describe())
            
            return details.getvalue()
        finally:
            sys.stdout = old_stdout
    
    async def analyze(self, query: str, timeout: int = 60) -> AsyncGenerator[str, None]:
        """
        Process a user query about the DataFrame and yield results.
        
        Args:
            query: The user's question about the DataFrame
            timeout: Maximum time in seconds to wait for a response
            
        Yields:
            JSON strings containing response chunks
        """
        if not hasattr(self, 'df') or self.df is None:
            yield json.dumps({"chunk": "No DataFrame loaded. Please upload a CSV file first."})
            return
        
        # Make sure plotly express is available at the module level
        global px
        if 'px' not in globals():
            import plotly.express as px
        
        # Handle basic dataset description questions
        describe_pattern = re.compile(r'(describe|summarize|tell me about|what\'s in|show me|explain) (the|this) (data|dataset|table|dataframe)', re.IGNORECASE)
        if describe_pattern.search(query):
            # Create a visualization of column counts
            try:
                # Generate a basic overview visualization
                fig = None
                visualization_html = None
                
                # Only attempt visualization if plotly is available
                if self._plotly_available:
                    # Use plotly to create a column data types visualization
                    column_types = self.df.dtypes.astype(str).value_counts()
                    if len(column_types) > 0:
                        try:
                            import plotly.express as px
                            fig = px.pie(
                                values=column_types.values, 
                                names=column_types.index, 
                                title="Column Data Types Distribution"
                            )
                            visualization_html = fig.to_html(full_html=False, include_plotlyjs='cdn')
                        except Exception as viz_error:
                            logger.error(f"Error creating visualization: {str(viz_error)}")
                
                # Provide basic description from our collected dataset details
                description = f"This dataset has {self.df.shape[0]} rows and {self.df.shape[1]} columns.\n\n"
                description += f"The columns are: {', '.join(self.df.columns)}\n\n"
                description += f"Here's a sample of the data (first 5 rows):\n{self.df.head(5).to_string()}"
                
                # Return response with or without visualization
                if visualization_html:
                    yield json.dumps({
                        "chunk": description,
                        "visualization": visualization_html,
                        "is_local_llm": True
                    })
                else:
                    yield json.dumps({
                        "chunk": description,
                        "is_local_llm": True
                    })
                
            except Exception as e:
                logger.error(f"Error generating dataset overview: {str(e)}")
                # Fallback to basic text description
                description = f"This dataset has {self.df.shape[0]} rows and {self.df.shape[1]} columns.\n\n"
                description += f"The columns are: {', '.join(self.df.columns)}"
                
                yield json.dumps({
                    "chunk": description,
                    "is_local_llm": True
                })
            
            return
        
        try:
            # Create a prompt that matches the Streamlit implementation
            message = f"""You are a data analysis assistant. You have access to a DataFrame named 'df'. When analyzing this DataFrame, follow these rules:

1. For calculations:
   - NEVER create sample data or new DataFrames
   - ALWAYS use the existing 'df' DataFrame
   - Use Python code to calculate exact values
   - Print results with print()
   - DO NOT modify calculated values
   - DO NOT print the figure with print(fig) - this will break the visualization

2. For visualizations:
   - Use plotly.express as px
   - Always save plots to a variable named 'fig'
   - Create beautiful and professional visualizations
   - Include clear titles and labels
   - For count plots, sort the data chronologically
   - Use color='Count' for gradient effects in bar plots
   - IMPORTANT: NEVER EVER use print(fig) - this WILL BREAK the visualization
   - Just create the figure and assign it to 'fig' - DO NOT print it, display it, or show it

Example for counting and plotting:
Thought: I need to create a count plot by Model Year
Action: python_repl_ast
Action Input: 
import plotly.express as px

# Get value counts and create plot
counts = df['Model Year'].value_counts().reset_index()
counts.columns = ['Model Year', 'Count']
counts = counts.sort_values('Model Year')  # Sort chronologically

# Create beautiful visualization with gradient
fig = px.bar(counts, 
             x='Model Year', 
             y='Count',
             color='Count',  # This creates a gradient based on count values
             title='Vehicle Distribution by Model Year',
             labels={{'Model Year': 'Model Year', 'Count': 'Number of Vehicles'}})

# Enhance the layout
fig.update_layout(
    template="plotly_white",
    bargap=0.2,
    plot_bgcolor="white",
    paper_bgcolor="white",
    showlegend=False,
    coloraxis_showscale=False  # Hide color scale
)

# CRITICAL: NEVER use print(fig) - it will NOT display properly
# ❌ DO NOT DO THIS: print(fig)  
# ✅ DO THIS: just define fig and let the system handle display

THE DATASET DETAILS:
{self.dataset_details}

USER QUESTION: 
{query}

Format your response with code wrapped in ```python and ``` markers.
"""
            
            # Get response from LLM with timeout
            response_future = asyncio.create_task(self.llm.ainvoke(message))
            response = await asyncio.wait_for(response_future, timeout)
            
            # Extract the content from AIMessage if needed
            if hasattr(response, 'content'):
                response_text = response.content
            else:
                response_text = str(response)
            
            # Extract Python code from the response
            code_pattern = r"```python\s*(.*?)\s*```"
            code_match = re.search(code_pattern, response_text, re.DOTALL)
            
            if not code_match:
                yield json.dumps({
                    "chunk": f"I couldn't generate code to answer your question. Please try rephrasing your query.",
                    "is_local_llm": True
                })
                return
            
            # Get the code and log it
            code = code_match.group(1).strip()
            
            # Remove any print(fig) statements that would break the visualization
            code = re.sub(r'print\s*\(\s*fig\s*\)', '# print(fig) - removed', code)
            
            logger.info(f"Generated code: {code}")
            
            # Create a safe execution environment with all required imports
            local_vars = {
                "df": self.df.copy(), 
                "np": np, 
                "pd": pd
            }
            
            # Ensure px is imported and available in local_vars if plotly is available
            if self._plotly_available:
                try:
                    import plotly.express as px
                    local_vars["px"] = px
                    # Add enhanced plotly configuration
                    import plotly.io as pio
                    pio.templates.default = "plotly_white"  # Set default template
                    local_vars["pio"] = pio
                except ImportError:
                    logger.warning("Could not import plotly express (px). Visualizations will not be available.")
            
            # Capture stdout to get printed output
            old_stdout = sys.stdout
            mystdout = io.StringIO()
            sys.stdout = mystdout
            
            # Execute the code
            try:
                # Ensure df is in both globals and locals for exec
                globals_dict = globals().copy()
                globals_dict["df"] = self.df.copy()
                
                exec(code, globals_dict, local_vars)
                output = mystdout.getvalue()
                
                # Check if a plotly figure was created
                fig = None
                has_visualization = False
                
                # First, look for a fig variable in local_vars
                for var_name, var_value in local_vars.items():
                    if var_name == 'fig' and 'plotly' in str(type(var_value)):
                        fig = var_value
                        has_visualization = True
                        break
                
                # If no fig was found but we see a Figure object in the output, warn about it
                if not has_visualization and 'Figure(' in output:
                    logger.warning("Figure may have been printed instead of saved to a variable")
                    # We can't recover the figure, so we'll just have to rely on the text output
                    # This prevents blank outputs when the user sees a figure in the terminal
                
                # Capture visualization HTML if present
                visualization_html = None
                if fig:
                    try:
                        visualization_html = fig.to_html(full_html=False, include_plotlyjs='cdn')
                    except Exception as viz_error:
                        logger.error(f"Error creating visualization HTML: {str(viz_error)}")
                
                # Send the output directly to the LLM with a simple prompt
                interpretation_message = f"""Give a clear, direct answer to the user's question: "{query}"

Based on the analysis results:
{output}

Keep your answer concise and focused on the key insights from the data. Speak in first person as if you did the analysis yourself."""
                
                # If there's a visualization, add a note about it
                if has_visualization:
                    interpretation_message += """

Note: I've created a visualization to better illustrate these insights."""
                
                # Get LLM's interpretation of the results
                interpretation = await self.llm.ainvoke(interpretation_message)
                
                # Extract content from AIMessage if needed
                if hasattr(interpretation, 'content'):
                    interpretation_text = interpretation.content
                else:
                    interpretation_text = str(interpretation)
                
                # Format the final result with only the LLM's interpretation (and visualization if present)
                if visualization_html:
                    # Use a special JSON structure to separate text content from visualization
                    # This will allow the frontend to properly render the visualization
                    response_json = json.dumps({
                        "chunk": interpretation_text,
                        "visualization": visualization_html,
                        "is_local_llm": True
                    })
                else:
                    response_json = json.dumps({
                        "chunk": interpretation_text,
                        "is_local_llm": True
                    })
                
                yield response_json
                
            except Exception as e:
                error_msg = f"Error executing code: {str(e)}"
                logger.error(error_msg)
                
                # Provide a more user-friendly error message through the LLM
                error_message = f"""You are a helpful data analysis assistant. 

A user asked this question about a dataset: "{query}"

When trying to analyze the data, this error occurred: "{str(e)}"

Provide a brief, simple explanation of what might have gone wrong and suggest alternatives
or a better way to ask the question. Be helpful and concise."""
                
                try:
                    # Get a user-friendly explanation of the error
                    error_explanation = await self.llm.ainvoke(error_message)
                    
                    # Extract content from AIMessage if needed
                    if hasattr(error_explanation, 'content'):
                        error_explanation_text = error_explanation.content
                    else:
                        error_explanation_text = str(error_explanation)
                    
                    yield json.dumps({
                        "chunk": error_explanation_text,
                        "is_local_llm": True
                    })
                except Exception:
                    # Fallback to simple error message if LLM fails
                    yield json.dumps({
                        "chunk": f"Error: {error_msg}. Please try rephrasing your question or checking if the data contains the information you're looking for.",
                        "is_local_llm": True
                    })
            finally:
                # Restore stdout
                sys.stdout = old_stdout
                
        except asyncio.TimeoutError:
            logger.warning(f"Query timed out after {timeout} seconds: {query[:100]}...")
            yield json.dumps({
                "chunk": f"Analysis timed out after {timeout} seconds. Please try a simpler query or increase the timeout limit.",
                "is_local_llm": True
            })
        except Exception as e:
            error_msg = f"Error processing query: {str(e)}"
            logger.error(error_msg)
            yield json.dumps({
                "chunk": f"Error during analysis: {error_msg}",
                "is_local_llm": True
            })



