from openai import OpenAI
import json
import inspect
from typing import Dict, Callable, Any, List, Optional
from system_prompt import SystemPrompt
from tools import Tools  # Import the Tools class
import os
from dotenv import load_dotenv

load_dotenv('.env.local')
# Get the KEY from .env file
KEY = os.getenv("OPENROUTER_API_KEY")



def sql_query(query: str) -> List[tuple]:
    """
    Execute a SQL query on the SQLite database.
    
    Args:
        query (str): The SQL query to execute
    Returns:
        List[tuple]: The query results as a list of tuples
    """
    import sqlite3
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute(query)
        result = cursor.fetchall()
        conn.close()
        return result
    except Exception as e:
        return [("Error executing query:", str(e))]







class LLM:
    def __init__(self):
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=KEY
        )
        self.tools: Dict[str, Dict[str, Any]] = {}
        
        # Register SQL query tool by default
        self.register_tool("sql_query", sql_query)

        # Instantiate the Tools class
        self.tool_instance = Tools()

        # Register the Tools class methods
        self.register_tools_from_class(self.tool_instance) #New line
        
    def register_tool(self, name: str, func: Callable) -> None:
        """
        Register a tool function with its description.
        
        Args:
            name (str): The name of the tool
            func (Callable): The function to register as a tool
        """
        # Get function signature and docstring
        sig = inspect.signature(func)
        doc = inspect.getdoc(func) or "No description available"
        
        # Extract parameters information
        params = {}
        for param_name, param in sig.parameters.items():
            param_info = {
                "type": str(param.annotation) if param.annotation != inspect.Parameter.empty else "str",
                "required": param.default == inspect.Parameter.empty
            }
            params[param_name] = param_info
            
        self.tools[name] = {
            "function": func,
            "description": doc,
            "parameters": params
        }
        print(f"[DEBUG] Registered tool: {name}")
    
    def register_tools_from_class(self, tool_instance):
        """
        Registers all methods from a class as tools.
        """
        for name in dir(tool_instance):
            method = getattr(tool_instance, name)
            if callable(method) and not name.startswith("__"):  # Avoid private methods
                self.register_tool(name, method)
        
    def get_tools_description(self) -> str:
        """
        Generate a string description of all available tools.
        
        Returns:
            str: A formatted string describing all available tools
        """
        if not self.tools:
            return "No tools available."
            
        descriptions = ["Available tools:"]
        for name, tool_info in self.tools.items():
            descriptions.append(f"\n- {name}: {tool_info['description']}")
            if tool_info['parameters']:
                descriptions.append("  Parameters:")
                for param_name, param_info in tool_info['parameters'].items():
                    required = "required" if param_info['required'] else "optional"
                    descriptions.append(f"    - {param_name} ({param_info['type']}): {required}")
        
        return "\n".join(descriptions)
        
    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Execute a tool with the given arguments.
        
        Args:
            tool_name (str): The name of the tool to execute
            arguments (Dict[str, Any]): The arguments to pass to the tool
            
        Returns:
            Any: The result of the tool execution
        """
        if tool_name not in self.tools:
            return f"Error: Tool '{tool_name}' not found. Available tools: {list(self.tools.keys())}"
            
        try:
            tool_func = self.tools[tool_name]["function"]
            result = tool_func(**arguments)
            print(f"[DEBUG] Tool '{tool_name}' executed successfully")
            return result
        except Exception as e:
            error_msg = f"Error executing tool '{tool_name}': {str(e)}"
            print(f"[DEBUG] {error_msg}")
            return error_msg
            
    def parse_tool_call(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Parse the response to extract tool call information.
        
        Args:
            response (str): The LLM response to parse
            
        Returns:
            Optional[Dict[str, Any]]: The parsed tool call or None
        """
        try:
            # Look for JSON-like tool call in the response
            if "tool_call" in response:
                # Extract JSON part
                start = response.find("{")
                end = response.rfind("}") + 1
                if start != -1 and end != 0:
                    json_str = response[start:end]
                    tool_call_data = json.loads(json_str)
                    return tool_call_data.get("tool_call")
        except (json.JSONDecodeError, AttributeError):
            pass
        return None

    def get_completion(self, prompt: str, system_prompt_override: Optional[str] = None, max_tool_calls: int = 5) -> str:
        """
        Get completion from LLM with tool calling support.
        
        Args:
            prompt (str): The user prompt
            system_prompt_override (Optional[str]): Override the default system prompt
            max_tool_calls (int): Maximum number of tool calls to prevent infinite loops
            
        Returns:
            str: The final response after all tool calls
        """
        current_system_prompt = system_prompt_override or SystemPrompt().system_prompt
        tools_description = self.get_tools_description()
        full_system_prompt = f"{current_system_prompt}\n\n{tools_description}"
        
        conversation_history = []
        tool_call_count = 0
        
        # Initial user prompt
        current_prompt = prompt
        
        while tool_call_count < max_tool_calls:
            try:
                completion = self.client.chat.completions.create(
                    extra_headers={
                        "HTTP-Referer": "<YOUR_SITE_URL>",
                        "X-Title": "<YOUR_SITE_NAME>",
                    },
                    extra_body={},
                    model="deepseek/deepseek-r1-0528:free", 
                    messages=[
                        {
                            "role": "user",
                            "content": f"{full_system_prompt}\n\n\nAnd this is the actual user prompt: {current_prompt}"
                        }
                    ]
                )
                
                response = completion.choices[0].message.content
                print(f"[DEBUG] LLM Response: {response[:200]}...")
                
                # Check if the response contains a tool call
                tool_call = self.parse_tool_call(response)
                
                if tool_call:
                    tool_name = tool_call.get("name")
                    arguments = tool_call.get("arguments", {})
                    
                    print(f"[DEBUG] Tool call detected: {tool_name} with args: {arguments}")
                    
                    # Execute the tool
                    tool_result = self.execute_tool(tool_name, arguments)
                    
                    # Update the prompt with tool result for next iteration
                    current_prompt = f"Previous tool call result:\nTool: {tool_name}\nArguments: {arguments}\nResult: {tool_result}\n\nOriginal user prompt: {prompt}\n\nPlease provide your final response based on the tool result."
                    
                    tool_call_count += 1
                    conversation_history.append({
                        "tool_call": tool_call,
                        "tool_result": tool_result
                    })
                else:
                    # No tool call, return the response
                    print(f"[DEBUG] No tool call detected, returning final response")
                    return response
                    
            except Exception as e:
                error_msg = f"Error during completion: {str(e)}"
                print(f"[DEBUG] {error_msg}")
                return error_msg
        
        return f"Maximum tool calls ({max_tool_calls}) reached. Conversation history: {conversation_history}"

