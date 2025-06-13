# -*- coding: utf-8 -*-
"""ultimate_reval_agent.py ─ merged v1

A **unified** agent that fuses the best of `ultimate_steelmill_agent.py`
(patched v2) and `reval_llm_agent.py`.

───────────────────────────────────────────────────────────────────────────────
Key Features
────────────
• **ReVAL loop** (Reason‑Verify‑Adapt‑Loop) with confidence gating & self‑reflection.
• Dual **tool‑calling** strategy: native OpenAI function‑calling *or* JSON fallback.
• **ScratchPad** with TTL + automatic large‑payload off‑loading.
• Built‑in **meta‑tools** (goal‑state store, complexity estimator, verifier, etc.).
• Automatic **toolsmith** (create & test new tools on‑the‑fly).
• Robust **guard‑rails**: strict JSON schema, timeout sandbox, adaptive token trim.
• Drop‑in compatibility with any project already using `tools.py` helpers.

Dependencies: tiktoken, pydantic, python‑dotenv, openai>=1.0.0
"""
from __future__ import annotations

###############################################################################
# 0.  Imports & global helpers
###############################################################################
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
from openai import (
    APIConnectionError,
    AsyncOpenAI,
    OpenAIError,
    RateLimitError,
)
from pydantic import BaseModel, Field, ValidationError, create_model

###############################################################################
# 1.  Primitive helpers – Tool decorator & ScratchPad
###############################################################################
@dataclass
class ToolSpec:
    name: str
    description: str
    args_schema: Type[BaseModel]
    handler: Callable[..., Awaitable[Any]]

def tool(desc: str = "") -> Callable[[Callable], Callable]:
    """Decorator that turns a function/method into a registered *tool*."""

    def decorator(func: Callable):
        sig = inspect.signature(func)
        fields: Dict[str, tuple] = {}
        for pname, param in sig.parameters.items():
            if pname == "self":
                continue
            annot = (
                param.annotation
                if param.annotation is not inspect.Parameter.empty
                else Any
            )
            default = (
                ... if param.default is inspect.Parameter.empty else param.default
            )
            fields[pname] = (annot, Field(default=default))
        ArgsModel = create_model(f"{func.__name__.title()}Args", **fields)  # type: ignore

        async def _wrapper(*args, **kwargs):
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

        func.__tool_spec__ = ToolSpec(  # type: ignore[attr-defined]
            func.__name__, desc or func.__doc__ or "", ArgsModel, _wrapper
        )
        return func

    return decorator


class ScratchPad(dict):
    """In‑memory TTL‑aware key‑value store (auto‑cleans on access)."""

    def store(self, value: Any, ttl: Optional[int] = None) -> str:
        key = f"sp_{uuid.uuid4().hex[:8]}"
        expiry = time.time() + ttl if ttl else None
        super().__setitem__(key, (value, expiry))
        return key

    def load(self, key: str):
        if key not in self:
            raise KeyError(key)
        val, exp = self[key]
        if exp and exp < time.time():
            del self[key]
            raise KeyError(f"{key} expired")
        return val

###############################################################################
# 2.  UltimateReVALAgent – core engine
###############################################################################
class UltimateReVALAgent:
    """Merged agent implementing ReVAL + Ultimate features."""

    # Regex to capture JSON blocks in fallback mode
    _JSON_RE = re.compile(r"```json\s*([\s\S]*?)```", re.I)

    STRICT_JSON_ERROR = (
        "⛔️ Format invalide. Réponds UNIQUEMENT par un bloc ```json``` contenant `tool_call`."
    )

    def __init__(
        self,
        model: str = "deepseek/deepseek-r1-0528:free",
        *,
        tool_support: bool = False,
        temperature: float = 0.2,
        max_model_tokens: int = 16_000,
        max_response_tokens: int = 2_048,
        persona_prompt: str | None = None,
        debug: bool = True,
    ) -> None:
        # ── ENV & LLM client ────────────────────────────────────────────────
        load_dotenv(".env.local")
        api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("Missing API key env var")
        self.client = AsyncOpenAI(api_key=api_key, timeout=45)

        # ── core settings ───────────────────────────────────────────────────
        self.model = model
        self.tool_support_flag = tool_support
        self.temperature = temperature
        self.max_model_tokens = max_model_tokens
        self.max_response_tokens = max_response_tokens
        self._enc = tiktoken.get_encoding("cl100k_base")
        self.debug = debug

        # ── runtime state ───────────────────────────────────────────────────
        self.scratch = ScratchPad()
        self.tools: Dict[str, ToolSpec] = {}
        self._fc_supported: Optional[bool] = None  # unknown until first attempt

        # ── logging ─────────────────────────────────────────────────────────
        self.log = logging.getLogger("UltimateReVAL")
        self.log.setLevel(logging.INFO)
        if debug:
            logging.basicConfig(stream=sys.stdout, level=logging.INFO)

        # ── register built‑in tools ─────────────────────────────────────────
        self.register_tool(self.update_goal_state)
        self.register_tool(self.save_to_scratchpad)
        self.register_tool(self.load_from_scratchpad)
        self.register_tool(self.self_reflect_and_replan)
        self.register_tool(self.complexity_estimator)
        self.register_tool(self.simple_verifier)
        self.register_tool(self.create_and_test_tool)

        # ── system prompt ───────────────────────────────────────────────────
        self.persona_prompt = (
            persona_prompt or "You are SteelMillAI, an elite autonomous agent known for rigorous reasoning and brutal honesty."
        )
        self._refresh_system_prompt()

    # ======================================================================
    # Tool registration & helpers
    # ======================================================================
    def register_tool(self, func: Callable):
        """Register a callable that has been decorated with @tool."""
        if not hasattr(func, "__tool_spec__"):
            func = tool()(func)  # auto‑decorate if not already
        spec: ToolSpec = func.__tool_spec__  # type: ignore[attr-defined]
        self.tools[spec.name] = spec
        self._refresh_system_prompt()

    def register_tools_from_instance(self, obj: Any):
        for name in dir(obj):
            if name.startswith("_"):
                continue
            attr = getattr(obj, name)
            if callable(attr):
                self.register_tool(attr if inspect.ismethod(attr) else attr.__get__(obj))

    # ----------------------------------------------------------------------
    # Built‑in meta tools
    # ----------------------------------------------------------------------
    @tool("Update or query long‑term goal‑state store.")
    async def update_goal_state(
        self,
        original_request: Optional[str] = None,
        plan: Optional[List[str]] = None,
        completed_step: Optional[str] = None,
        finding_key: Optional[str] = None,
        finding_value: Optional[Any] = None,
        confidence: Optional[float] = None,
    ) -> Dict[str, Any]:
        gs = self.scratch.setdefault(
            "goal_state", {"plan": [], "done": [], "findings": {}, "conf": None}
        )
        if original_request:
            gs["request"] = original_request
        if plan is not None:
            gs["plan"] = plan
        if completed_step:
            gs["done"].append(completed_step)
        if finding_key and finding_value is not None:
            gs["findings"][finding_key] = finding_value
        if confidence is not None:
            gs["conf"] = confidence
        return gs

    @tool("Persist data into scratchpad; returns key.")
    async def save_to_scratchpad(self, value: Any, ttl_s: int | None = None) -> str:
        return self.scratch.store(value, ttl_s)

    @tool("Retrieve value from scratchpad by key.")
    async def load_from_scratchpad(self, key: str):
        try:
            return self.scratch.load(key)
        except KeyError as err:
            return {"error": str(err)}

    @tool("Self‑reflect: critique current plan and propose new one.")
    async def self_reflect_and_replan(self, critique: str, new_plan: List[str]):
        return {"meta": "reflect", "critique": critique, "plan": new_plan}

    # ── ReVAL specific tools ───────────────────────────────────────────────
    @tool("Estimate problem complexity (0‑1) for dynamic budgeting.")
    async def complexity_estimator(self, prompt: str) -> float:
        score = min(len(prompt.split()) / 4000, 1.0)
        return score

    @tool("Simple self‑verifier. Returns True if answer likely correct (stub).")
    async def simple_verifier(self, answer: str, question: str) -> bool:
        # Placeholder implementation; always returns True.
        return True

    # ── Dynamic toolsmith ──────────────────────────────────────────────────
    @tool("Create a new Python tool, test it, and register it if tests pass.")
    async def create_and_test_tool(
        self,
        tool_name: str,
        description: str,
        python_code: str,
        test_code: str,
    ) -> str:
        ns: Dict[str, Any] = {}
        exec(python_code, globals(), ns)
        if tool_name not in ns:
            return "Error: function not defined."
        fn = ns[tool_name]
        exec(test_code, globals(), {"candidate": fn})
        setattr(self, tool_name, fn.__get__(self))
        self.register_tool(getattr(self, tool_name))
        self.tools[tool_name].description = description  # type: ignore
        return f"Tool '{tool_name}' created and registered."

    # ======================================================================
    # System prompt
    # ======================================================================
    def _refresh_system_prompt(self):
        tool_lines = []
        for spec in self.tools.values():
            params = ", ".join(
                spec.args_schema.model_json_schema().get("properties", {}).keys()
            )
            tool_lines.append(f"- `{spec.name}({params})`: {spec.description}")
        tools_doc = "\n".join(tool_lines)
        usage_doc = (
            "Tools are available via *native function‑calling* (if supported) **or** via a JSON fall‑back.\n\n"  # noqa: E501
            "When using the fall‑back, reply **only** with one JSON block:\n"
            "```json\n{\"tool_call\": {\"name\": <tool_name>, \"arguments\": {…}}}\n```"
        )
        self.system_prompt = f"{self.persona_prompt}\n\n### Tools\n{tools_doc}\n\n### Usage\n{usage_doc}"

    # ======================================================================
    # LLM invocation helpers
    # ======================================================================
    async def _call_llm(self, messages: List[Dict]) -> Dict:
        """Call the LLM with graceful degradation between modes."""
        want_native = self.tool_support_flag or (self._fc_supported is not False)
        fc_schema = None
        if want_native:
            fc_schema = [
                {
                    "type": "function",
                    "function": {
                        "name": s.name,
                        "description": s.description,
                        "parameters": s.args_schema.model_json_schema(),
                    },
                }
                for s in self.tools.values()
            ]
        params = dict(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_response_tokens,
            tools=fc_schema if want_native else None,
            tool_choice="auto" if want_native else None,
        )
        for attempt in range(3):
            try:
                resp = await self.client.chat.completions.create(**params)
                self._fc_supported = want_native
                return resp.choices[0].message.model_dump()
            except OpenAIError as err:
                if want_native and (
                    getattr(err, "status_code", None) == 404 or "No endpoints" in str(err)
                ):
                    # function‑calling not supported → downgrade once
                    self._fc_supported = False
                    want_native = False
                    params["tools"] = None
                    params["tool_choice"] = None
                    continue
                if isinstance(err, (RateLimitError, APIConnectionError)):
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise
        raise RuntimeError("LLM failed after retries")

    # ======================================================================
    # Tool execution helper (with large‑payload off‑loading)
    # ======================================================================
    async def _execute_tool(self, name: str, args: Dict[str, Any]):
        if name not in self.tools:
            return {"error": f"Unknown tool {name}"}
        spec = self.tools[name]
        try:
            validated = spec.args_schema(**args)
            result = await spec.handler(**validated.dict())
            # Large payload? → off‑load to scratchpad
            if (
                isinstance(result, (dict, list, str))
                and len(json.dumps(result, default=str)) > 4000
            ):
                key = self.scratch.store(result, ttl=300)
                return {"scratchpad_key": key, "info": f"{name} output stored (large payload)"}
            return result
        except ValidationError as ve:
            return {"error": str(ve)}
        except Exception as exc:  # noqa: B902
            return {"error": str(exc)}

    # ======================================================================
    # Parsing helpers
    # ======================================================================
    def _extract_tool_calls(self, resp: Dict) -> Optional[List[Dict]]:
        """Return a list of tool‑call dicts or None (for both modes)."""
        # Native function‑calling
        if resp.get("tool_calls"):
            return resp["tool_calls"]
        # JSON fall‑back parsing
        content = resp.get("content")
        if not content:
            return None
        m = self._JSON_RE.search(content)
        if not m:
            return None
        try:
            blob = json.loads(m.group(1))
            if "tool_call" in blob and {"name", "arguments"} <= set(blob["tool_call"].keys()):
                tc = blob["tool_call"]
                return [
                    {
                        "id": f"tc_{uuid.uuid4().hex[:6]}",
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": json.dumps(tc["arguments"]),
                        },
                    }
                ]
        except Exception:
            return None
        return None

    def _tool_messages(self, calls: List[Dict], results: List[Any]):
        msgs = []
        for call, res in zip(calls, results):
            msgs.append(
                {
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "name": call["function"]["name"],
                    "content": json.dumps(res, default=str)[:12_000],
                }
            )
        return msgs

    # ======================================================================
    # Utility
    # ======================================================================
    def _tokens(self, txt: str | None) -> int:
        return len(self._enc.encode(txt or ""))

    def _trim(self, msgs: List[Dict]):
        budget = self.max_model_tokens - self.max_response_tokens
        while sum(self._tokens(m.get("content")) for m in msgs) > budget and len(msgs) > 3:
            msgs.pop(1)
        return msgs

    # ======================================================================
    # Chat loop (ReVAL)
    # ======================================================================
    async def chat(self, user_prompt: str, history: Optional[List[Dict]] = None) -> str:
        history = history or []
        msgs: List[Dict] = [
            {"role": "system", "content": self.system_prompt},
            *history,
            {"role": "user", "content": user_prompt},
        ]
        await self.update_goal_state(original_request=user_prompt)

        for _ in range(10):  # max ReVAL cycles
            msgs = self._trim(msgs)
            assistant = await self._call_llm(msgs)
            msgs.append(assistant)

            # Confidence gating (look for CONF=x.y in content)
            conf_match = re.search(r"CONF\s*=\s*([0-9.]+)", assistant.get("content", ""))
            if conf_match:
                conf_val = float(conf_match.group(1))
                await self.update_goal_state(confidence=conf_val)
                if conf_val < 0.7:
                    reflection = await self.self_reflect_and_replan(
                        critique="Low confidence", new_plan=["Retry with deeper reasoning"]
                    )
                    msgs.append({"role": "assistant", "content": json.dumps(reflection)})
                    continue

            # Tool phase
            tool_calls = self._extract_tool_calls(assistant)
            if not tool_calls:
                return assistant.get("content", "")

            async def timed_exec(call):
                try:
                    return await asyncio.wait_for(
                        self._execute_tool(
                            call["function"]["name"],
                            json.loads(call["function"]["arguments"]),
                        ),
                        timeout=25,
                    )
                except asyncio.TimeoutError:
                    return {"error": "tool timeout"}

            results = await asyncio.gather(*[timed_exec(c) for c in tool_calls])

            # Verification pass (stub – verify first result)
            if results:
                ok = await self.simple_verifier(answer=str(results[0]), question=user_prompt)
                if not ok:
                    reflection = await self.self_reflect_and_replan(
                        critique="Verifier failed", new_plan=["Revise answer"]
                    )
                    msgs.append({"role": "assistant", "content": json.dumps(reflection)})
                    continue

            msgs.extend(self._tool_messages(tool_calls, results))
        return "⚠️ Reached max reasoning cycles."

###############################################################################
# 3.  Demo driver (optional)
###############################################################################
if __name__ == "__main__":
    async def _demo():
        try:
            from toolsv2 import SteelMillTools as DomainTools  # Your project‑specific helpers
        except ImportError:
            class DomainTools:  # fallback dummy
                @tool("Returns 42")
                def dummy(self):
                    return 42
        agent = UltimateReVALAgent(tool_support=True)
        agent.register_tools_from_instance(DomainTools())
        answer = await agent.chat("Calcule la consommation électrique totale et donne la CONF.")
        print("\n=== ANSWER ===\n", answer)

    asyncio.run(_demo())
