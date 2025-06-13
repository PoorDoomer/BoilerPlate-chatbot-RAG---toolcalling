
import sys

from toolsv2 import SteelMillTools
# Fix for Unicode display issues on Windows consoles
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')



# -*- coding: utf-8 -*-
"""ultimate_steelmill_agent.py  –  patched v3

* FIX: Adds `sys.stdout.reconfigure(encoding='utf-8')` to prevent UnicodeEncodeError on Windows.
* Adds missing `_run_tool()` method (fixes AttributeError).
* Implements placeholder domain-specific tools for a complete, runnable example.
* Adds a main interactive loop.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import os
import re
import sys
import time
import uuid
from dataclasses import dataclass
from functools import partial
from typing import Any, Awaitable, Callable, Dict, List, Optional, Type

import tiktoken
from dotenv import load_dotenv
from openai import AsyncOpenAI, APIConnectionError, RateLimitError
from pydantic import BaseModel, Field, ValidationError, create_model

# -----------------------------------------------------------------------------
# 0.  DEBUG UTILITIES
# -----------------------------------------------------------------------------
DEBUG = bool(int(os.getenv("ULTIMATE_DEBUG", "0")))

def dprint(*args: Any, **kwargs: Any):
    """
    Safe debug print pour consoles Windows : remplace
    tout caractère non encodable par '?' afin d’éviter
    le RuntimeWarning / UnicodeEncodeError.
    """
    if not DEBUG:
        return
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        safe_args = [
            str(a).encode(sys.stdout.encoding or "ascii", "replace")
                  .decode(sys.stdout.encoding or "ascii", "replace")
            for a in args
        ]
        print(*safe_args, **kwargs)


# -----------------------------------------------------------------------------
# 1.  Low-level primitives: Tool decorator + ScratchPad
# -----------------------------------------------------------------------------

@dataclass
class ToolSpec:
    name: str
    description: str
    args_schema: Type[BaseModel]
    handler: Callable[..., Awaitable[Any]]


def tool(description: str):
    """Decorator that registers an async or sync Python function as a tool."""

    def decorator(func: Callable):
        sig = inspect.signature(func)
        fields: Dict[str, tuple] = {}
        for pname, param in sig.parameters.items():
            if pname == "self":
                continue
            ann = (
                param.annotation
                if param.annotation is not inspect.Parameter.empty
                else Any
            )
            fields[pname] = (
                ann,
                Field(default=param.default)
                if param.default is not inspect.Parameter.empty
                else ...,
            )
        ArgsModel = create_model(f"{func.__name__.title()}Args", **fields)  # type: ignore

        async def _async_wrapper(*args, **kwargs):
            # dprint(f"[TOOL] {func.__name__} called → {kwargs}")
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, partial(func, *args, **kwargs))

        _async_wrapper.__tool_spec__ = ToolSpec(  # type: ignore[attr-defined]
            name=func.__name__,
            description=description or func.__doc__ or "No description",
            args_schema=ArgsModel,
            handler=_async_wrapper,
        )
        return _async_wrapper

    return decorator


class ScratchPad(dict):
    def store(self, value: Any, ttl_s: int | None = None) -> str:
        key = f"sp_{uuid.uuid4().hex[:8]}"
        super().__setitem__(key, (value, time.time() + ttl_s if ttl_s else None))
        return key

    def load(self, key: str) -> Any:
        if key not in self:
            raise KeyError(f"{key} not found")
        val, exp = self[key]
        if exp and exp < time.time():
            del self[key]
            raise KeyError(f"{key} expired")
        return val

# -----------------------------------------------------------------------------
# 2.  Domain-Specific Tools (Steel Mill)
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# 3.  UltimateAgent – main cognitive engine
# -----------------------------------------------------------------------------

JSON_BLOCK_RE = re.compile(r"```json\s*(\{[\s\S]*?\})\s*```", re.IGNORECASE)
STRICT_JSON_ERROR = (
    "⛔️ Format invalide. Réponds UNIQUEMENT par un bloc ```json``` contenant `tool_call`."
)

class UltimateAgent:
    def __init__(
        self,
        model: str = "deepseek/deepseek-coder-v2:free", # Using a coder model
        *,
        tool_support: bool = False,
        max_model_tokens: int = 16_000,
        max_response_tokens: int = 4_096,
        temperature: float = 0.1,
        persona_prompt: str | None = None,
    ) -> None:
        load_dotenv(".env.local")
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY missing in .env.local")
        self.client = AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key, timeout=45)

        self.model = model
        self.tool_support = tool_support
        self.max_model_tokens = max_model_tokens
        self.max_response_tokens = max_response_tokens
        self.temperature = temperature
        self._enc = tiktoken.get_encoding("cl100k_base")
        self._log = logging.getLogger("UltimateAgent")
        self._log.setLevel(logging.INFO)

        self.scratchpad = ScratchPad()
        self._tools: Dict[str, ToolSpec] = {}

        self._register_builtin_tools()

        self.persona_prompt = persona_prompt or "You are SteelMillAI, an elite autonomous agent."
        self.system_prompt = self._build_system_prompt()

    # ------------------------------------------------------------------ tools

    def _register_builtin_tools(self):
        self.register_tool(self.update_goal_state)
        self.register_tool(self.save_to_scratchpad)
        self.register_tool(self.load_from_scratchpad)
        self.register_tool(self.self_reflect_and_replan)
        self.register_tool(self.create_and_test_tool)

    def register_tool(self, fn: Callable):
        spec: ToolSpec | None = getattr(fn, "__tool_spec__", None)
        if not spec:
            fn = tool(fn.__doc__ or "No description")(fn)
            spec = fn.__tool_spec__  # type: ignore[attr-defined]
        if inspect.ismethod(fn):
            orig = spec.handler
            self_ref = fn.__self__

            async def _bound_handler(**kw):
                return await orig(self_ref, **kw)

            spec.handler = _bound_handler
        self._tools[spec.name] = spec

    def register_tools_from_instance(self, obj: Any):
        for name in dir(obj):
            if name.startswith("_"):
                continue
            attr = getattr(obj, name)
            if callable(attr) and hasattr(attr, "__tool_spec__"):
                self.register_tool(attr)


    # ---------------------------- built‑in meta‑tools -------------------------

    @tool("Persist an object in scratchpad and return its key.")
    async def save_to_scratchpad(self, value: Any, ttl_s: int | None = None) -> str:  # type: ignore[override]
        return self.scratchpad.store(value, ttl_s)

    @tool("Retrieve an object from scratchpad with its key.")
    async def load_from_scratchpad(self, key: str) -> Any:  # type: ignore[override]
        try:
            return self.scratchpad.load(key)
        except KeyError as exc:
            return {"error": str(exc)}

    @tool("Update or query current goal state.")
    async def update_goal_state(
        self,
        original_request: str | None = None,
        plan: List[str] | None = None,
        completed_step: str | None = None,
        finding_key: str | None = None,
        finding_value: Any | None = None,
    ) -> Dict[str, Any]:
        gs = self.scratchpad.setdefault("goal_state", {"plan": [], "done": [], "findings": {}})
        if original_request:
            gs["request"] = original_request
        if plan is not None:
            gs["plan"] = plan
        if completed_step:
            gs["done"].append(completed_step)
        if finding_key and finding_value is not None:
            gs["findings"][finding_key] = finding_value
        return gs

    @tool("Self‑reflect when stuck and propose a new plan.")
    async def self_reflect_and_replan(self, critique: str, new_plan: List[str]) -> Dict[str, Any]:
        return {"meta": "reflect", "critique": critique, "plan": new_plan}

    @tool("Create a new Python tool, test it, and register it if tests pass.")
    async def create_and_test_tool(self, tool_name: str, description: str, python_code: str, test_code: str) -> str:
        ns: Dict[str, Any] = {}
        exec(python_code, globals(), ns)
        if tool_name not in ns:
            return "Error: function not defined."
        fn = ns[tool_name]
        exec(test_code, globals(), {"candidate": fn})
        setattr(self, tool_name, fn.__get__(self))
        self.register_tool(getattr(self, tool_name))
        self._tools[tool_name].description = description
        return f"Tool '{tool_name}' created and registered."

    # ------------------------------------------------------------------ system prompt helpers

    def _tools_doc(self) -> str:
        return "\n".join(
            f"- `{sp.name}({', '.join(sp.args_schema.model_json_schema()['properties'].keys())})`: {sp.description}"
            for sp in self._tools.values()
        )

    def _build_system_prompt(self) -> str:
        return (
            f"{self.persona_prompt}\n\n"
            "### STRICT Manual Tool Calling\n"
            "Réponds UNIQUEMENT par un bloc JSON contenant `tool_call`.\n"
            "Exemple :```json\n{""\"tool_call\""": {""\"name\""": ""\"my_tool\""", ""\"arguments\""": {}}}""```\n"
            "Here are your available tools:\n" + self._tools_doc() + "\n\n"
        )

    # ------------------------------------------------------------------ JSON parsing / validation

    def _validate_tool_call_json(self, obj: Dict[str, Any]) -> bool:
        if not (isinstance(obj, dict) and "tool_call" in obj):
            return False
        tc = obj["tool_call"]
        if not (isinstance(tc, dict) and len(tc) == 2 and {"name", "arguments"} <= tc.keys()):
            return False
        name, arguments = tc["name"], tc["arguments"]
        if name not in self._tools or not isinstance(arguments, dict):
            return False
        try:
            self._tools[name].args_schema(**arguments)
        except ValidationError:
            return False
        return True

    def _parse_tool_calls(self, assistant: Dict[str, Any]) -> List[Dict[str, Any]] | None:
        if assistant.get("tool_calls"):
            return assistant["tool_calls"]
        content = assistant.get("content", "")
        if not content:
            return None
            
        all_calls = []
        for match in JSON_BLOCK_RE.finditer(content):
            try:
                blob = json.loads(match.group(1))
                if not self._validate_tool_call_json(blob):
                    continue
                tc = blob["tool_call"]
                all_calls.append(
                    {
                        "id": f"call_{uuid.uuid4().hex[:8]}",
                        "type": "function",
                        "function": {"name": tc["name"], "arguments": json.dumps(tc["arguments"])}
                    }
                )
            except (json.JSONDecodeError, ValidationError):
                continue
        return all_calls if all_calls else None


    # ------------------------------------------------------------------ tool executor

    async def _run_tool(self, name: str, args: Dict[str, Any]) -> Any:
        if name not in self._tools:
            return {"error": f"Unknown tool {name}"}
        spec = self._tools[name]
        try:
            validated = spec.args_schema(**args)
            result = await spec.handler(**validated.model_dump())
            if isinstance(result, (dict, list, str)) and len(json.dumps(result)) > 4000:
                key = self.scratchpad.store(result, ttl_s=300)
                return {"scratchpad_key": key, "info": f"{name} output stored (large payload)"}
            return result
        except ValidationError as exc:
            return {"error": str(exc)}
        except Exception as exc:
            return {"error": f"Tool execution failed: {exc}"}

    # ---------------------------------------------------------------------
    # Chat loop
    # ---------------------------------------------------------------------

    async def chat(self, user_prompt: str, history: List[Dict[str, Any]] | None = None) -> str:
        history = history or []
        self.system_prompt = self._build_system_prompt()

        msgs: List[Dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt},
            *history,
            {"role": "user", "content": user_prompt},
        ]

        await self.update_goal_state(original_request=user_prompt)

        for i in range(10):  # max cycles
            dprint(f"\n--- CYCLE {i+1} ---\nMessages so far: {len(msgs)}")
            msgs = self._trim(msgs)
            assistant = await self._llm(msgs)
            dprint(f"ASSISTANT RAW: {assistant.get('content')}")
            msgs.append(assistant)

            calls = self._parse_tool_calls(assistant)

            if not calls:
                if assistant.get("content"):
                    return assistant["content"]
                msgs.append({"role": "system", "content": STRICT_JSON_ERROR})
                continue
            
            dprint(f"PARSED CALLS: {[c['function']['name'] for c in calls]}")

            results = await asyncio.gather(
                *[
                    self._run_tool(c["function"]["name"], json.loads(c["function"]["arguments"]))
                    for c in calls
                ]
            )
            for c, r in zip(calls, results):
                dprint(f"TOOL RESULT ({c['function']['name']}): {r}")
                msgs.append(
                    {
                        "role": "tool",
                        "tool_call_id": c["id"],
                        "name": c["function"]["name"],
                        "content": json.dumps(r, default=str)[:12_000],
                    }
                )
        return "⚠️ Max cycles reached. The agent may be stuck in a loop."

    # ---------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------

    async def _llm(self, messages: List[Dict[str, Any]], retries: int = 3) -> Dict[str, Any]:
        params = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_response_tokens,
        }
        for attempt in range(retries):
            try:
                resp = await self.client.chat.completions.create(**params)
                return resp.choices[0].message.model_dump(exclude_unset=True)
            except (RateLimitError, APIConnectionError) as err:
                self._log.warning("LLM err %s – retry", err)
                await asyncio.sleep(2 ** attempt)
        raise RuntimeError("LLM failed after retries")

    def _tokens(self, txt: str | None) -> int:
        return len(self._enc.encode(txt or "")) if txt else 0

    def _trim(self, msgs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        budget = self.max_model_tokens - self.max_response_tokens
        current_tokens = sum(self._tokens(m.get("content")) for m in msgs)
        
        while current_tokens > budget and len(msgs) > 2: # Keep system and first user prompt
            removed_msg = msgs.pop(1) # Remove from the start of the history
            current_tokens -= self._tokens(removed_msg.get("content"))
            dprint(f"TRIM: Removed message. Tokens now: {current_tokens}")

        return msgs


# -----------------------------------------------------------------------------
# 4.  Main Execution Block
# -----------------------------------------------------------------------------
async def main():
    """Main function to run the interactive agent."""
    # --- FIX FOR UNICODE ERRORS ON WINDOWS ---
    if sys.stdout.encoding.lower() != 'utf-8':
        print("--> Reconfiguring console encoding to UTF-8 to support Unicode characters.")
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    # -----------------------------------------
    
    print("Initializing Ultimate Agent…")
    agent = UltimateAgent()
    
    # Register domain-specific tools
    steel_tools = SteelMillTools()
    agent.register_tools_from_instance(steel_tools)
    
    print(f"→ {len(agent._tools)} tools loaded: {', '.join(agent._tools.keys())}\n")
    print("================================================================")
    print("||   ULTIMATE AI AGENT — STEELMILLAI   ||")
    print("================================================================")
    print("\nCommands: !exit, !reset — JSON only when calling tools.\n")
    
    history = []
    while True:
        try:
            user_prompt = input("You › ")
            if user_prompt.lower() == '!exit':
                print("Exiting agent.")
                break
            if user_prompt.lower() == '!reset':
                print("Resetting agent state and history.")
                history = []
                agent.scratchpad.clear()
                continue

            response = await agent.chat(user_prompt, history=history)
            
            # Add user prompt and AI response to history for context in next turn
            history.append({"role": "user", "content": user_prompt})
            history.append({"role": "assistant", "content": response})

            print(f"\nSteelMillAI › {response}\n")

        except KeyboardInterrupt:
            print("\nExiting agent.")
            break
        except Exception as e:
            print(f"Unexpected error: {e}")


if __name__ == "__main__":
    # To use this script, make sure you have a .env.local file with:
    # OPENROUTER_API_KEY="your_api_key"
    try:
        asyncio.run(main())
    except RuntimeError as e:
        print(f"An error occurred: {e}")
