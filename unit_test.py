#TESTING MULTIPLE QUESTIONS TO THE LLMs
import sqlite3
import os
import unittest
from llm import LLM
import json


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

print(f"{bcolors.WARNING}Warning: TESTING IS GONNA START. {bcolors.ENDC}")

connection = sqlite3.connect("databasevf.db")

from dotenv import load_dotenv

load_dotenv('.env.local')

# Get the KEY from .env.local file
KEY = os.getenv("QWEN")
print(f"KEY: {KEY}")
agent = LLM()

def log_test(question,answer,get_completion,success):
    with open("test_results.json", "a") as f:
        f.write(json.dumps({"question":question,"answer":answer,"get_completion":get_completion,"success":success}) + ",\n")


def contains_number(number,text) -> bool:
    no_comma_text = text.replace(",","")
    
    return number in no_comma_text

class TestLLM(unittest.TestCase):
    def test_questions(self):
        with open("qa.json", "r") as f:
            data = json.load(f)
        for question in data["questions"]:
            print(f"{bcolors.OKGREEN}TESTING IS STARTING for QUESTION: {question['question']}. {bcolors.ENDC}") 
            get_completion = agent.get_completion(question["question"])
            success = contains_number(question["answer"],get_completion)
            log_test(question["question"],question["answer"],get_completion,success)
            self.assertTrue(success,f"{question['answer']} is not in the text")
            print(f"{bcolors.OKGREEN}TESTING IS DONE for QUESTION: {question['question']}. {bcolors.ENDC}")


    




if __name__ == "__main__":
    unittest.main()


