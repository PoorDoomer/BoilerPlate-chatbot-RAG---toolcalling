from litellm import completion
import os
from dotenv import load_dotenv
from RAG.rag import RAG
load_dotenv()

## set ENV variables
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")


messages = [{ "content": "Hello, how are you?","role": "user"}]

# openai call
response = completion(model="openai/gpt-4o", messages=messages)

# anthropic call
print(response)


class LLM:
    def __init__(self):
        self.messages = []
        self.model = "openai/gpt-4o"
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.system_prompt = "You are a helpful assistant"
        self.tools = []
        self.memory = []
        self.rag_enabled = False
        self.rag = RAG()

    def add_message(self, message):
        self.messages.append(message)

    def get_response(self):
        response = completion(model=self.model, messages=self.messages)
        return response

    def get_tools(self):
        pass 


