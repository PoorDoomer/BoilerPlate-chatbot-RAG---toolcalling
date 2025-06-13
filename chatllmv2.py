# --- Filename: chat_manager.py ---

from typing import List, Dict, Any, Optional
from ulti_llm import UltimateAgent # The new engine
from system_prompt import SystemPrompt # Your custom prompt
import re
import os
import datetime

class ChatManager:
    """
    Manages a conversation session with the UltimateAgent.
    - Maintains chat history.
    - Handles the async interaction with the agent.
    - Interprets structured agent responses for the UI.
    - Supports logging mode for debugging.
    """

    def __init__(self, agent: UltimateAgent, log_mode: bool = False):
        self.agent: UltimateAgent = agent
        self.history: List[Dict[str, Any]] = []
        self.system_prompt_loader = SystemPrompt()
        self.log_mode = log_mode
        self.log_file = None
        
        if self.log_mode:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            self.log_file = f"chat_log_{timestamp}.log"
            with open(self.log_file, "w") as f:
                f.write(f"=== Chat Session Log Started at {datetime.datetime.now()} ===\n\n")
            self._log(f"Chat Manager initialized with agent: {agent}")

    def _log(self, message: str):
        """Write a message to the log file if log mode is enabled."""
        if self.log_mode and self.log_file:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(self.log_file, "a") as f:
                f.write(f"[{timestamp}] {message}\n")

    async def send_message(self, user_message: str) -> Dict[str, Any]:
        """
        Sends a user message to the agent and returns a structured response for the UI.
        """
        # Load your custom system prompt
        system_prompt = self.system_prompt_loader.system_prompt
        
        self._log(f"User message: {user_message}")
        self._log(f"Current history length: {len(self.history)}")
        
        # The agent's chat method is now the main entry point
        final_content = await self.agent.chat(user_message, self.history)
        self._log(f"Agent response: {final_content[:100]}..." if len(final_content) > 100 else final_content)
        
        # Update history
        self.history.append({"role": "user", "content": user_message})
        self.history.append({"role": "assistant", "content": final_content})
        self._log(f"History updated, new length: {len(self.history)}")

        # --- INNOVATION: Structured Interactive Response ---
        # Check if the final content is a path to a file
        if ".html" in final_content or ".png" in final_content:
            # Extract the path (simple regex for robustness)
            path_match = re.search(r'at: ([\w\\/.:-]+\.(?:html|png))', final_content)
            if path_match:
                artifact_path = path_match.group(1)
                self._log(f"Artifact detected: {artifact_path}")
                return {
                    "status": "artifact_ready",
                    "message": f"I have generated the dashboard for you.",
                    "artifact_path": artifact_path
                }
        
        return {
            "status": "completed",
            "message": final_content,
            "artifact_path": None
        }

    def reset_history(self):
        """Clears the conversation history."""
        self._log("Resetting history and scratchpad")
        self.history.clear()
        self.agent.scratchpad.clear() # Also clear the agent's scratchpad