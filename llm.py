import re
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
print("[DEBUG] API Key loaded:", KEY[:5] + "*" * 10 + (KEY[-5:] if KEY else "Not found"))


TOOL_TAG_RE = re.compile(
    r"tool▁call▁begin.*?tool▁sep.*?(\w+)\s*```json\s*([\s\S]+?)```",
    re.DOTALL
)

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
        print("[DEBUG] Executing SQL query:", query)
        conn = sqlite3.connect('databasevf.db')
        cursor = conn.cursor()
        cursor.execute(query)
        result = cursor.fetchall()
        conn.close()
        print("[DEBUG] SQL query result count:", len(result))
        return result
    except Exception as e:
        print("[DEBUG] SQL query error:", str(e))
        return [("Error executing query:", str(e))]







class LLM:
    def __init__(self):
        print("[DEBUG] Initializing LLM")
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=KEY
        )
        self.tools: Dict[str, Dict[str, Any]] = {}
        
        # NEW: Initialize the scratchpad for persistent storage
        self.scratchpad: Dict[str, Any] = {}
        
        # Register SQL query tool by default
        self.register_tool("sql_query", sql_query)

        # Instantiate the Tools class
        self.tool_instance = Tools()

        # Register the Tools class methods
        self.register_tools_from_class(self.tool_instance) #New line
        
        # NEW: Register scratchpad tools
        self.register_tool(
            "save_to_scratchpad", 
            self.save_to_scratchpad
        )
        self.register_tool(
            "load_from_scratchpad", 
            self.load_from_scratchpad
        )
        
        print("[DEBUG] LLM initialization complete")
        
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
        print("[DEBUG] Registering tools from class")
        for name in dir(tool_instance):
            method = getattr(tool_instance, name)
            if callable(method) and not name.startswith("__"):  # Avoid private methods
                self.register_tool(name, method)
        print(f"[DEBUG] Total tools registered: {len(self.tools)}")
        
    # NEW: Scratchpad helper methods
    def save_to_scratchpad(self, key: str, value: Any) -> str:
        """
        Saves a key-value pair to a persistent scratchpad for later use.
        
        Args:
            key (str): The unique identifier to store the value under
            value (Any): The data to store
            
        Returns:
            str: Confirmation message
        """
        self.scratchpad[key] = value
        print(f"[DEBUG] Saved to scratchpad with key: '{key}'")
        return f"Value saved to scratchpad with key: '{key}'"
        
    def load_from_scratchpad(self, key: str) -> Any:
        """
        Loads a value from the persistent scratchpad using its key.
        
        Args:
            key (str): The unique identifier of the stored data
            
        Returns:
            Any: The stored data or error message if key not found
        """
        if key in self.scratchpad:
            print(f"[DEBUG] Loaded from scratchpad with key: '{key}'")
            return self.scratchpad.get(key)
        print(f"[DEBUG] Key '{key}' not found in scratchpad")
        return f"Error: Key '{key}' not found in scratchpad."
        
    def _generate_scratchpad_key(self, prefix: str = "result") -> str:
        """
        Helper to create unique keys for the scratchpad.
        
        Args:
            prefix (str): Prefix for the key
            
        Returns:
            str: A unique key
        """
        import uuid
        return f"{prefix}_{uuid.uuid4().hex[:6]}"
        
    def get_tools_description(self) -> str:
        """
        Generate a string description of all available tools.
        
        Returns:
            str: A formatted string describing all available tools
        """
        print("[DEBUG] Generating tools description")
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
        print(f"[DEBUG] Executing tool: {tool_name} with arguments: {arguments}")
        if tool_name not in self.tools:
            print(f"[DEBUG] Tool '{tool_name}' not found")
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


    
    def parse_tool_call(self,msg:str):
        print("[DEBUG] Parsing tool call from message")
        
        # 1) Format natif {"tool_call": …}
        blocks = re.findall(r"```json\s*([\s\S]*?)\s*```", msg)
        for b in blocks:
            try:
                # Normalize whitespace and newlines in JSON before parsing
                normalized_json = re.sub(r'(?<!\\)\n', '\\n', b)
                obj = json.loads(normalized_json)
                if "tool_call" in obj:
                    print(f"[DEBUG] Found tool call in JSON format: {obj['tool_call']['name']}")
                    return obj["tool_call"]
            except json.JSONDecodeError as e:
                print(f"[DEBUG] JSON decode error in tool call parsing: {str(e)}")
                # Try to fix common JSON errors
                try:
                    # Fix trailing commas
                    fixed_json = re.sub(r',\s*}', '}', b)
                    fixed_json = re.sub(r',\s*]', ']', fixed_json)
                    # Normalize newlines in strings
                    fixed_json = re.sub(r'(?<!\\)\n', '\\n', fixed_json)
                    obj = json.loads(fixed_json)
                    if "tool_call" in obj:
                        print(f"[DEBUG] Found tool call after fixing JSON: {obj['tool_call']['name']}")
                        return obj["tool_call"]
                except Exception:
                    print("[DEBUG] Failed to fix JSON format")
                    pass

        # 2) Try direct JSON format without tool_call wrapper
        for b in blocks:
            try:
                # Normalize whitespace and newlines in JSON before parsing
                normalized_json = re.sub(r'(?<!\\)\n', '\\n', b)
                obj = json.loads(normalized_json)
                if "name" in obj and "arguments" in obj:
                    print(f"[DEBUG] Found direct tool call format: {obj['name']}")
                    return obj
            except json.JSONDecodeError as e:
                print(f"[DEBUG] JSON decode error in direct format parsing: {str(e)}")
                # Try to fix common JSON errors
                try:
                    # Fix trailing commas
                    fixed_json = re.sub(r',\s*}', '}', b)
                    fixed_json = re.sub(r',\s*]', ']', fixed_json)
                    # Normalize newlines in strings
                    fixed_json = re.sub(r'(?<!\\)\n', '\\n', fixed_json)
                    obj = json.loads(fixed_json)
                    if "name" in obj and "arguments" in obj:
                        print(f"[DEBUG] Found direct tool call after fixing JSON: {obj['name']}")
                        return obj
                except Exception:
                    print("[DEBUG] Failed to fix JSON format")
                    pass
                
        # 3) Fallback : balises <|tool▁call▁begin|>
        m = TOOL_TAG_RE.search(msg)
        if m:
            try:
                name = m.group(1)
                args_text = m.group(2)
                # Normalize whitespace and newlines in JSON before parsing
                normalized_json = re.sub(r'(?<!\\)\n', '\\n', args_text)
                args = json.loads(normalized_json)
                print(f"[DEBUG] Found tool call using regex: {name}")
                return {"name": name, "arguments": args}
            except json.JSONDecodeError as e:
                print(f"[DEBUG] JSON decode error in regex pattern: {str(e)}")
                # Try to fix common JSON errors
                try:
                    # Fix trailing commas
                    fixed_json = re.sub(r',\s*}', '}', args_text)
                    fixed_json = re.sub(r',\s*]', ']', fixed_json)
                    # Normalize newlines in strings
                    fixed_json = re.sub(r'(?<!\\)\n', '\\n', fixed_json)
                    args = json.loads(fixed_json)
                    print(f"[DEBUG] Found tool call after fixing JSON: {name}")
                    return {"name": name, "arguments": args}
                except Exception:
                    print("[DEBUG] Failed to fix JSON format")
                    pass

        # 4) Last attempt: Try to find any JSON object with name and arguments
        try:
            # Look for any JSON-like structure in the message
            potential_json_matches = re.finditer(r'{[\s\S]*?}', msg)
            for match in potential_json_matches:
                try:
                    json_str = match.group(0)
                    # Normalize whitespace and newlines in JSON before parsing
                    normalized_json = re.sub(r'(?<!\\)\n', '\\n', json_str)
                    obj = json.loads(normalized_json)
                    
                    # Check for tool_call wrapper
                    if "tool_call" in obj and "name" in obj["tool_call"] and "arguments" in obj["tool_call"]:
                        print(f"[DEBUG] Found tool call in raw JSON: {obj['tool_call']['name']}")
                        return obj["tool_call"]
                    
                    # Check for direct format
                    if "name" in obj and "arguments" in obj:
                        print(f"[DEBUG] Found tool call in raw JSON: {obj['name']}")
                        return obj
                except json.JSONDecodeError as e:
                    print(f"[DEBUG] Failed to parse potential JSON match: {str(e)}")
                    # Try to fix common JSON errors
                    try:
                        # Fix trailing commas
                        fixed_json = re.sub(r',\s*}', '}', json_str)
                        fixed_json = re.sub(r',\s*]', ']', fixed_json)
                        # Normalize newlines in strings
                        fixed_json = re.sub(r'(?<!\\)\n', '\\n', fixed_json)
                        obj = json.loads(fixed_json)
                        
                        # Check for tool_call wrapper
                        if "tool_call" in obj and "name" in obj["tool_call"] and "arguments" in obj["tool_call"]:
                            print(f"[DEBUG] Found tool call after fixing JSON: {obj['tool_call']['name']}")
                            return obj["tool_call"]
                        
                        # Check for direct format
                        if "name" in obj and "arguments" in obj:
                            print(f"[DEBUG] Found tool call after fixing JSON: {obj['name']}")
                            return obj
                    except Exception:
                        print("[DEBUG] Failed to fix JSON format")
                        continue
        except Exception as e:
            print(f"[DEBUG] Failed to parse raw JSON: {str(e)}")
            pass

        # 5) Special case: Fix SQL query fragments with line breaks
        try:
            # Look for tool_call with sql_query and fix the query parameter
            sql_pattern = re.search(r'{\s*"tool_call"\s*:\s*{\s*"name"\s*:\s*"sql_query"\s*,\s*"arguments"\s*:\s*{\s*"query"\s*:\s*"(.*?)"\s*}\s*}\s*}', msg, re.DOTALL)
            if sql_pattern:
                query_text = sql_pattern.group(1)
                # Clean up the query text - remove unescaped newlines and trailing fragments
                clean_query = re.sub(r'(?<!\\)\n', ' ', query_text)
                # Remove any trailing fragments that might cause JSON parsing issues
                clean_query = re.sub(r',\s*\w+,\s*$', '', clean_query)
                clean_query = re.sub(r'\w+,\s*$', '', clean_query)
                clean_query = re.sub(r'\w+;\s*"\s*$', '"', clean_query)
                
                fixed_json = f'{{"tool_call": {{"name": "sql_query", "arguments": {{"query": "{clean_query}"}}}}}}'
                obj = json.loads(fixed_json)
                print(f"[DEBUG] Fixed SQL query tool call")
                return obj["tool_call"]
        except Exception as e:
            print(f"[DEBUG] Failed to fix SQL query: {str(e)}")
            pass

        print("[DEBUG] No tool call found in message")
        return None
    
    def clean_response_for_context(self, response: str) -> str:
        """
        Clean assistant response for inclusion in conversation context.
        Removes tool calls and formats the reasoning part for ReAct pattern.
        
        Args:
            response (str): The assistant's response to clean
            
        Returns:
            str: Cleaned response suitable for context
        """
        print("[DEBUG] Cleaning response for context")
        # Remove JSON tool calls using regex
        cleaned = re.sub(r'```json\s*{.*?}\s*```', '', response, flags=re.DOTALL)
        
        # Remove excessive whitespace and newlines
        cleaned = re.sub(r'\n\s*\n\s*\n+', '\n\n', cleaned)
        cleaned = cleaned.strip()
        
        # Extract reasoning/thinking part (before tool calls typically)
        if cleaned:
            # Keep only the reasoning part, typically before tool execution
            reasoning_match = re.search(r'^(.*?)(?=\n*(?:I need to|Let me|I should|I will use))', cleaned, re.DOTALL | re.IGNORECASE)
            if reasoning_match:
                cleaned = reasoning_match.group(1).strip()
        
        print(f"[DEBUG] Cleaned response length: {len(cleaned)}")
        return cleaned if cleaned else ""


    def get_completion(
        self,
        prompt: str,
        system_prompt_override: Optional[str] = None,
        max_tool_calls: int = 10
    ) -> str:
        """
        Boucle ReAct complète : appels d'outils, gestion des rôles,
        nettoyage du HTML final.
        """
        print(f"[DEBUG] Getting completion for prompt: {prompt[:50]}...")

        # ────────────────────────────────────────────────────────────
        # 1) Prépare les messages "system"
        # ────────────────────────────────────────────────────────────
        sys_base  = system_prompt_override or SystemPrompt().system_prompt
        sys_tools = self.get_tools_description()

        chat_history = [
            {"role": "system", "content": sys_base},
            {"role": "system", "content": sys_tools},
            {"role": "user",   "content": prompt},
        ]

        tool_call_count = 0
        print(f"[DEBUG] Starting ReAct loop with max {max_tool_calls} tool calls")

        # ────────────────────────────────────────────────────────────
        # 2) Boucle ReAct
        # ────────────────────────────────────────────────────────────
        while tool_call_count < max_tool_calls:
            print(f"[DEBUG] ReAct iteration {tool_call_count + 1}")
            completion = self.client.chat.completions.create(
                model="deepseek/deepseek-r1-0528:free",
                messages=chat_history,
                extra_headers={
                    "HTTP-Referer": "<YOUR_SITE_URL>",
                    "X-Title": "<YOUR_SITE_NAME>",
                },
            )

            assistant_msg = completion.choices[0].message
            content       = assistant_msg.content or ""
            chat_history.append({"role": "assistant", "content": content})

            print(f"[DEBUG] LLM Response: {content[:200]}...")

            # ── 2.a Détection de l'appel d'outil ────────────────────
            tool_call = self.parse_tool_call(content)
            if not tool_call:
                # Pas d'appel d'outil ⇒ réponse finale
                print("[DEBUG] No tool call detected, returning final response")
                cleaned = _extract_html_if_any(content)
                return cleaned

            name      = tool_call.get("name")
            arguments = tool_call.get("arguments", {})

            print(f"[DEBUG] Tool call detected: {name} with args: {arguments}")
            tool_result = self.execute_tool(name, arguments)

            # Mettez à jour la liste de composants si on vient de builder le dashboard
            if name == "assemble_dashboard" and isinstance(arguments, dict):
                self.dashboard_components = arguments.get("components", [])
                print(f"[DEBUG] Updated dashboard components: {len(self.dashboard_components)} items")

            # ── 2.b Ajout du message rôle "tool" avec gestion intelligente des gros résultats ─────
            tool_content_for_history = ""
            
            # Define what constitutes a "large" result
            is_large_result = False
            result_size = 0
            
            if isinstance(tool_result, list):
                result_size = len(tool_result)
                is_large_result = result_size > 10  # More than 10 items is considered large
            
            try:
                payload = json.dumps(tool_result, ensure_ascii=False, default=str)
                print(f"[DEBUG] Tool result serialized, length: {len(payload)}")
                # Also consider character length for string results
                is_large_result = is_large_result or len(payload) > 1000  # More than 1000 chars is large
            except TypeError:
                print("[DEBUG] Failed to serialize tool result")
                payload = json.dumps({"error": "Unserialisable result"}, ensure_ascii=False)
                
            # Handle large results with the scratchpad pattern
            if is_large_result and name != "load_from_scratchpad":
                # The result is too big! Save it to the scratchpad
                key = self._generate_scratchpad_key(prefix=f"{name}_result")
                self.save_to_scratchpad(key, tool_result)
                
                # Create a summary message for the AI instead of the raw data
                summary = f"Tool '{name}' executed. Result is large ({result_size} items or {len(payload)} chars). "
                summary += f"It has been saved to your scratchpad with key '{key}'. "
                summary += "Use load_from_scratchpad to access it when needed."
                tool_content_for_history = summary
                print(f"[DEBUG] Large result detected. Saved to scratchpad with key '{key}'")
            else:
                # The result is small enough, pass it directly
                tool_content_for_history = payload

            chat_history.append({
                "role": "tool",
                "name": name,
                "content": tool_content_for_history
            })

            tool_call_count += 1

            # Gardez l'historique compact (20 messages max)
            if len(chat_history) > 20:
                print(f"[DEBUG] Trimming chat history from {len(chat_history)} to 20 messages")
                chat_history = chat_history[:2] + chat_history[-18:]

        # ────────────────────────────────────────────────────────────
        # 3) Sécurité : trop d'appels d'outil
        # ────────────────────────────────────────────────────────────
        print("[DEBUG] Max tool calls reached – aborting.")
        return "⚠️ J'ai atteint la limite d'appels d'outils."

# ────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────
def _extract_html_if_any(text: str) -> str:
    """
    Si la réponse finale est sous forme ```html …```, on enlève les backticks
    pour obtenir un vrai document HTML.
    """
    print("[DEBUG] Extracting HTML if present")
    match = re.search(r"```html\s*(.*?)\s*```", text, re.S | re.I)
    if match:
        print("[DEBUG] HTML content found and extracted")
        return match.group(1).strip()
    print("[DEBUG] No HTML content found, returning plain text")
    return text.strip()

def format_sql_for_json(sql_query: str) -> str:
    """
    Format a SQL query for safe inclusion in JSON.
    Handles multiline queries and escapes special characters.
    
    Args:
        sql_query (str): The SQL query to format
        
    Returns:
        str: JSON-safe SQL query string
    """
    # Remove comments
    sql_query = re.sub(r'--.*?$', '', sql_query, flags=re.MULTILINE)
    # Normalize whitespace
    sql_query = re.sub(r'\s+', ' ', sql_query)
    # Escape backslashes and double quotes
    sql_query = sql_query.replace('\\', '\\\\').replace('"', '\\"')
    # Remove any trailing commas or semicolons that might cause JSON issues
    sql_query = re.sub(r'[,;]\s*$', '', sql_query)
    
    return sql_query.strip()
