from llm import LLM


class ChatLLM(LLM):
    def __init__(self):
        super().__init__()
        self.messages = []
        self.system_prompt = "You are a helpful assistant. You are able to use tools to help the user."
        self.max_tool_calls = 10

    def chat(self,message:str):
        self.messages.append({"role":"user","content":message})
        response = self.get_completion(self.messages)
        self.messages.append({"role":"assistant","content":response})
        return response
    def set_system_prompt(self,system_prompt:str):
        self.system_prompt = system_prompt




