import pandas as pd
import sqlite3
import os
from llm import LLM

from dotenv import load_dotenv

load_dotenv('.env.local')

# Get the KEY from .env.local file
KEY = os.getenv("OPENROUTER_API_KEY")
print(KEY)
agent = LLM()

get_completion = agent.get_completion("Quel est la conso electrique  totale?")

print(get_completion)




# sheets = pd.read_excel("DATA-ACIERIE.xlsx",sheet_name=None)



# for sheet_name, df in sheets.items():
#     table_name = f'{sheet_name}'
#     df.to_sql(table_name, connection, if_exists="replace", index=False)
#     print(f"Table {table_name} created successfully")





#dataframe.to_sql("acierie", connection, if_exists="replace", index=False)

# print(dataframe.keys())

# print(dataframe.head())

