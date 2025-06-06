import pandas as pd
import sqlite3
import os
from llm import LLM
connection = sqlite3.connect("database.db")


agent = LLM()

get_completion = agent.get_completion("Get the names of the tables in the database")

print(get_completion)

sheets = pd.read_excel("DATA-ACIERIE.xlsx",sheet_name=None)








# for sheet_name, df in sheets.items():
#     table_name = f'{sheet_name}'
#     df.to_sql(table_name, connection, if_exists="replace", index=False)
#     print(f"Table {table_name} created successfully")





#dataframe.to_sql("acierie", connection, if_exists="replace", index=False)

# print(dataframe.keys())

# print(dataframe.head())

