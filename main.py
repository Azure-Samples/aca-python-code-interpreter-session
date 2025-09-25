import datetime
import os
import re

import dotenv
import httpx
from azure.identity import DefaultAzureCredential
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.ai.prompt_execution_settings import PromptExecutionSettings
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.functions.kernel_arguments import KernelArguments

dotenv.load_dotenv()

app = FastAPI()
templates = Jinja2Templates(directory="templates")

pool_management_endpoint = os.getenv("POOL_MANAGEMENT_ENDPOINT")
azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")

def auth_callback_factory(scope):
    auth_token = None

    async def auth_callback() -> str:
        """Auth callback for authentication with Azure services.
        This uses Azure's DefaultAzureCredential to get an access token.
        """
        nonlocal auth_token
        current_utc_timestamp = int(datetime.datetime.now(datetime.timezone.utc).timestamp())

        if not auth_token or auth_token.expires_on < current_utc_timestamp:
            credential = DefaultAzureCredential()
            auth_token = credential.get_token(scope)

        return auth_token.token
    
    return auth_callback


async def execute_python_code(code: str) -> dict:
    """Execute Python code using Azure Container Apps Session Pool via HTTP API."""
    if not pool_management_endpoint:
        return {
            "success": False,
            "error": "Session pool endpoint not configured",
            "output": ""
        }
    
    try:
        # Get authentication token with correct scope
        credential = DefaultAzureCredential()
        token = credential.get_token("https://dynamicsessions.io/.default")
        
        # Generate a session identifier (use timestamp for uniqueness)
        import uuid
        session_id = f"session-{uuid.uuid4().hex[:8]}"
        
        # Create session payload for code execution
        session_payload = {
            "properties": {
                "codeInputType": "inline",
                "executionType": "synchronous",
                "code": code
            }
        }
        
        headers = {
            "Authorization": f"Bearer {token.token}",
            "Content-Type": "application/json"
        }
        
        # Execute code via session pool API
        async with httpx.AsyncClient() as client:
            # Build the full URL for code execution
            execute_url = f"{pool_management_endpoint}/code/execute?api-version=2024-02-02-preview&identifier={session_id}"
            
            response = await client.post(
                execute_url,
                json=session_payload,
                headers=headers,
                timeout=60.0
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "output": result.get("properties", {}).get("stdout", ""),
                    "error": result.get("properties", {}).get("stderr", ""),
                    "result": result,
                    "session_id": session_id
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "output": ""
                }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "output": ""
        }


def extract_python_code(text: str) -> str:
    """Extract Python code from AI response."""
    # Look for code blocks marked with ```python
    python_code_pattern = r'```python\n(.*?)\n```'
    matches = re.findall(python_code_pattern, text, re.DOTALL)
    
    if matches:
        return matches[0].strip()
    
    # Look for code blocks marked with ```
    code_pattern = r'```\n(.*?)\n```'
    matches = re.findall(code_pattern, text, re.DOTALL)
    
    if matches:
        return matches[0].strip()
    
    # AGGRESSIVE: Check if the entire response looks like Python code
    lines = text.split('\n')
    python_lines = []
    
    # More aggressive detection for math/calculation responses
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('---'):  # Ignore separators
            # Check if line contains Python-like patterns
            if (stripped.startswith(('print(', 'import ', 'from ', 'def ', 'class ', 'if ', 'for ', 'while ', '#', 'result =', 'answer =', 'calc =')) or
                'print(' in stripped or 
                ' = ' in stripped and not stripped.startswith('#') or
                '**' in stripped or  # Power operator
                ' + ' in stripped or ' - ' in stripped or ' * ' in stripped or ' / ' in stripped or
                stripped.endswith(')') and ('(' in stripped)):  # Function calls
                python_lines.append(line)
    
    # If we found a significant amount of Python-like content, return it
    if python_lines and len(python_lines) >= 1:
        return '\n'.join(python_lines).strip()
    
    # FALLBACK: For simple math expressions, create Python code
    # Look for simple math patterns and convert them
    simple_math_patterns = [
        r'(\d+\s*[\+\-\*\/\*\*]\s*\d+)',  # Basic math operations
        r'(\d+\s*\*\*\s*\d+)',            # Power operations
        r'(\d+\s*%\s*\d+)',               # Modulo operations
    ]
    
    for pattern in simple_math_patterns:
        matches = re.findall(pattern, text)
        if matches:
            # Convert to Python code
            return f"result = {matches[0]}\nprint(result)"
    
    return ""


@app.get("/")
async def root():
    """Redirect to the chat UI"""
    return RedirectResponse("/ui")

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.datetime.now().isoformat()}

@app.get("/ui", response_class=HTMLResponse)
async def chat_ui(request: Request):
    """Serve the chat UI"""
    return templates.TemplateResponse("chat.html", {"request": request})


@app.get("/debug")
async def debug_info():
    """Debug endpoint to check environment variables."""
    return {
        "pool_endpoint": pool_management_endpoint,
        "azure_openai_endpoint": azure_openai_endpoint,
        "has_credentials": bool(pool_management_endpoint and azure_openai_endpoint)
    }


@app.get("/chat")
async def chat(message: str):
    """
    Chat endpoint that processes user messages using Semantic Kernel and Azure Session Pools.
    Can execute Python code for calculations and programming tasks.
    """
    print(f"DEBUG: Received message: {message}")
    print(f"DEBUG: Pool endpoint configured: {pool_management_endpoint}")
    
    kernel = Kernel()

    # Add Azure OpenAI chat completion service
    chat_service = AzureChatCompletion(
        service_id="chat-gpt",
        ad_token_provider=auth_callback_factory("https://cognitiveservices.azure.com/.default"),
        endpoint=azure_openai_endpoint,
        deployment_name="gpt-35-turbo",
    )
    kernel.add_service(chat_service)

    # Create a chat history with the user's message
    chat_history = ChatHistory()
    
    # Smart detection for math/calculation questions
    math_keywords = ['calculate', 'squared', 'square', 'root', 'solve', 'what is', 'what\'s', 'how much', 
                     'percentage', 'percent', 'times', 'multiply', 'divide', 'addition', 'subtract', 'plus', 'minus']
    math_operators = ['+', '-', '*', '/', '=', '^', '**', 'x', ' x ', '×']
    number_pattern = r'\b\d+\b'
    
    message_lower = message.lower()
    has_math_keywords = any(keyword in message_lower for keyword in math_keywords)
    has_math_operators = any(op in message_lower for op in math_operators)
    has_numbers = bool(re.search(number_pattern, message))
    
    # Enhanced detection: if it has numbers and math operators, or numbers and math keywords
    is_math_question = (has_numbers and has_math_operators) or (has_math_keywords and has_numbers)
    
    # Debug logging for math detection
    print(f"DEBUG: Math detection for '{message}':")
    print(f"DEBUG: has_math_keywords={has_math_keywords}, has_math_operators={has_math_operators}, has_numbers={has_numbers}")
    print(f"DEBUG: is_math_question={is_math_question}")
    
    if is_math_question:
        # Enhanced prompt for code generation
        enhanced_prompt = f"""You are an AI assistant that MUST use Python code execution for mathematical calculations.

CRITICAL RULES:
1. For math questions, you MUST write Python code
2. ALWAYS format Python code using ```python code blocks
3. Use print() statements to display results

User question: "{message}"

Provide Python code in ```python blocks that calculates and prints the answer."""
        chat_history.add_user_message(enhanced_prompt)
    else:
        # Regular conversation prompt
        regular_prompt = f"""You are a helpful AI assistant. Respond naturally to the user's question.

User: {message}"""
        chat_history.add_user_message(regular_prompt)
    
    try:
        # Create proper execution settings
        settings = PromptExecutionSettings(
            service_id="chat-gpt",
            max_tokens=500,
            temperature=0.7
        )
        
        # Get response from Azure OpenAI
        response = await chat_service.get_chat_message_contents(
            chat_history=chat_history,
            settings=settings,
            kernel=kernel,
            arguments=KernelArguments()
        )
        
        ai_response = str(response[0].content) if response and len(response) > 0 else "No response generated"
        
        # Check if the AI response contains Python code
        python_code = extract_python_code(ai_response)
        
        # Debug logging
        print(f"DEBUG: AI response length: {len(ai_response)}")
        print(f"DEBUG: Extracted Python code: {python_code}")
        print(f"DEBUG: Pool endpoint: {pool_management_endpoint}")
        
        result = {
            "output": ai_response,
            "note": "Response from Azure OpenAI via Semantic Kernel",
            "debug_extracted_code": python_code if python_code else "No Python code detected",
            "debug_pool_endpoint": pool_management_endpoint if pool_management_endpoint else "No pool endpoint configured",
            "debug_ai_response_length": len(ai_response),
            "debug_contains_code_blocks": "```python" in ai_response or "```" in ai_response
        }
        
        # If there's Python code AND it's a math question, execute it using session pools
        if python_code and pool_management_endpoint and is_math_question:
            try:
                execution_result = await execute_python_code(python_code)
                
                if execution_result["success"]:
                    result.update({
                        "code_executed": python_code,
                        "execution_output": execution_result["output"],
                        "execution_error": execution_result["error"] if execution_result["error"] else None,
                        "session_id": execution_result.get("session_id", "unknown"),
                        "note": "AI response with Python code executed in Azure Session Pool"
                    })
                else:
                    result.update({
                        "code_extracted": python_code,
                        "execution_failed": execution_result["error"],
                        "note": "AI response with Python code (execution failed)",
                        "debug_execution_result": execution_result
                    })
            except Exception as e:
                result.update({
                    "code_extracted": python_code,
                    "execution_exception": str(e),
                    "note": "AI response with Python code (execution error)"
                })
        elif python_code:
            result.update({
                "code_extracted": python_code,
                "note": f"AI response with Python code (session pool {'not configured' if not pool_management_endpoint else 'available'})"
            })
        
        return result
        
    except Exception as e:
        return {
            "output": f"Error: {str(e)}",
            "note": "There was an issue with the Azure OpenAI integration. Please check the logs.",
            "debug_info": {
                "azure_openai_endpoint": azure_openai_endpoint,
                "has_endpoint": bool(azure_openai_endpoint),
                "pool_endpoint": pool_management_endpoint
            }
        }
# Debug build 09/03/2025 20:04:55
