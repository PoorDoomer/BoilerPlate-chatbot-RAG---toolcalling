#!/usr/bin/env python3
"""test_v2.py — interactive CLI to chat with Ultimate SteelMillAI

Launch with:  `python test_v2.py`
Requires:
  • ultimate_steelmill_agent.py   (agent core)
  • toolsv2.py                    (domain‑specific tools)
  • chat_manager.py               (history + logging wrapper)

Environment variables expected:
  OPENROUTER_API_KEY   — your key for OpenRouter
  ULTIMATE_DEBUG       — optional, set « 0 » to silence debug prints
"""

import asyncio
import os
import webbrowser
from pathlib import Path

import colorama
from colorama import Fore, Style

# -----------------------------------------------------------------------------
# Local imports — make sure PYTHONPATH includes the project root
# -----------------------------------------------------------------------------
from ulti_llm import UltimateAgent
from toolsv2 import SteelMillTools
from chatllmv2 import ChatManager  # same logic as earlier versions

# -----------------------------------------------------------------------------
# CLI helpers
# -----------------------------------------------------------------------------
colorama.init(autoreset=True)
SPINNER = ["|", "/", "-", "\\"]


async def main() -> None:
    # 1) Initialise agent -------------------------------------------------------
    print(f"{Fore.YELLOW}Initializing Ultimate Agent…")
    agent = UltimateAgent(
        model="deepseek/deepseek-r1-0528:free",  # non‑native tool calling
        tool_support=False,
        persona_prompt=(
            "You are SteelMillAI, an elite autonomous agent for heavy‑industry analytics."
        ),
    )

    # 2) Register domain‑specific tools ----------------------------------------
    steel_tools = SteelMillTools()
    agent.register_tools_from_instance(steel_tools)

    print(
        f"{Fore.BLUE}→ {len(agent._tools)} tools loaded: "
        + ", ".join(agent._tools.keys())
    )

    # 3) Chat manager (keeps history + optional file log) ----------------------
    chat_manager = ChatManager(agent, log_mode=True)

    # 4) Welcome banner ---------------------------------------------------------
    print(f"\n{Fore.CYAN}{'=' * 64}")
    print(
        f"{Fore.CYAN}||{Style.BRIGHT}   ULTIMATE AI AGENT — STEELMILLAI   {Style.RESET_ALL}{Fore.CYAN}||"
    )
    print(f"{Fore.CYAN}{'=' * 64}\n")
    print(
        f"{Fore.GREEN}Commands: {Fore.RED}!exit{Fore.GREEN}, {Fore.RED}!reset{Fore.GREEN} — JSON only when calling tools."
    )

    # 5) Main REPL loop ---------------------------------------------------------
    while True:
        try:
            user_input = await asyncio.to_thread(
                input, f"\n{Style.BRIGHT + Fore.GREEN}You › {Style.RESET_ALL}"
            )
            if not user_input.strip():
                continue
            cmd = user_input.lower().strip()
            if cmd == "!exit":
                break
            if cmd == "!reset":
                chat_manager.reset_history()
                print(f"{Fore.YELLOW}Agent memory & history cleared.")
                continue

            # 5a) Run agent -----------------------------------------------------
            task = asyncio.create_task(chat_manager.send_message(user_input))
            i = 0
            while not task.done():
                print(f"{Fore.MAGENTA}\rAssistant is thinking… {SPINNER[i % 4]}", end="")
                await asyncio.sleep(0.2)
                i += 1
            print("\r" + " " * 40 + "\r", end="")  # clear spinner

            response = await task
            print(f"{Fore.CYAN + Style.BRIGHT}Assistant › {Style.RESET_ALL}{response['message']}")

            # 5b) Handle artifact (HTML dashboard, image, …) ------------------
            if response["status"] == "artifact_ready" and response["artifact_path"]:
                path = Path(response["artifact_path"]).expanduser()
                print(f"{Fore.YELLOW}Artifact saved at: {path}")
                try:
                    webbrowser.open(path.as_uri())
                    print(f"{Fore.GREEN}Opened in browser.")
                except Exception as exc:  # pragma: no cover
                    print(f"{Fore.RED}Could not open automatically: {exc}")

        except (KeyboardInterrupt, EOFError):
            break
        except Exception as exc:  # pragma: no cover
            print(f"{Fore.RED}\nUnexpected error: {exc}")

    print(f"\n{Fore.YELLOW}Session ended — goodbye!")


if __name__ == "__main__":
    asyncio.run(main())
