import pandas as pd
import sqlite3
import os

def excel_to_sqlite(excel_file, db_file):
    # Check if Excel file exists
    if not os.path.exists(excel_file):
        print(f"Error: {excel_file} not found!")
        return

    # Create a connection to the SQLite database
    conn = sqlite3.connect(db_file)
    
    try:
        # Read all sheets from the Excel file
        excel = pd.ExcelFile(excel_file)
        sheet_names = excel.sheet_names
        
        # Process each sheet
        for sheet_name in sheet_names:
            print(f"Processing sheet: {sheet_name}")
            
            # Read the sheet into a pandas DataFrame
            df = pd.read_excel(excel_file, sheet_name=sheet_name)
            
            
            
            # Write the DataFrame to SQLite
            df.to_sql(sheet_name, conn, if_exists='replace', index=False)
            print(f"Successfully imported {sheet_name} to database")
            
        print(f"\nAll sheets have been successfully imported to {db_file}")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    
    finally:
        # Close the database connection
        conn.close()

if __name__ == "__main__":
    excel_file = "DATA-ACIERIE.xlsx"
    db_file = "databasevf.db"
    excel_to_sqlite(excel_file, db_file)
