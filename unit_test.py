#TESTING MULTIPLE QUESTIONS TO THE LLMs
assert 1 < 0, "1 is not less than 0"
import sqlite3
import os
import unittest
from llm import LLM
import json




connection = sqlite3.connect("database.db")

from dotenv import load_dotenv

load_dotenv('.env.local')

# Get the KEY from .env.local file
KEY = os.getenv("OPENROUTER_API_KEY")
print(KEY)
agent = LLM()

def log_test(question,answer,get_completion,success):
    with open("test_results.json", "a") as f:
        f.write(json.dumps({"question":question,"answer":answer,"get_completion":get_completion,"success":success}) + ",\n")


def contains_number(number,text) -> bool:
    return number in text

class TestLLM(unittest.TestCase):
    def test_questions(self):
        with open("qa.json", "r") as f:
            data = json.load(f)
        for question in data["questions"]:
            get_completion = agent.get_completion(question["question"])
            success = contains_number(question["answer"],get_completion)
            log_test(question["question"],question["answer"],get_completion,success)
            self.assertTrue(success,f"{question['answer']} is not in the text")

    




if __name__ == "__main__":
    unittest.main()


