import pandas as pd
import sqlite3
import os
from llm import LLM
from chat_llm import ChatLLM
from dotenv import load_dotenv
import colorama
from colorama import Fore, Back, Style
import time
import sys
import re
import json
try:
    import readline  # For command history on Unix
except ImportError:
    # On Windows, use pyreadline or ignore
    try:
        import pyreadline
    except ImportError:
        pass

# Initialize colorama
colorama.init(autoreset=True)

load_dotenv('.env.local')

# Get the KEY from .env.local file
KEY = os.getenv("OPENROUTER_API_KEY")
print(f"{Fore.YELLOW}API Key loaded: {KEY[:5]}{'*' * 10}{KEY[-5:] if KEY else 'Not found'}")
agent = LLM()

# get_completion = agent.get_completion("Propose une liste de KPIs")

# print(get_completion)


# Initialize chat LLM
chat_llm = ChatLLM(debug=True)
print(chat_llm.system_prompt)
# Helper function to format JSON tool calls properly
def format_tool_call(tool_name, **kwargs):
    """
    Format a tool call as proper JSON to avoid parsing issues.
    
    Args:
        tool_name (str): The name of the tool to call
        **kwargs: The arguments for the tool
        
    Returns:
        str: A properly formatted JSON tool call
    """
    # For SQL queries, ensure they're properly formatted
    if tool_name == "sql_query" and "query" in kwargs:
        # Remove comments
        query = re.sub(r'--.*?$', '', kwargs["query"], flags=re.MULTILINE)
        # Normalize whitespace (replace newlines with spaces)
        query = re.sub(r'\s+', ' ', query)
        # Remove any trailing commas or semicolons that might cause JSON issues
        query = re.sub(r'[,;]\s*$', '', query)
        kwargs["query"] = query
        
    tool_call = {"tool_call": {"name": tool_name, "arguments": kwargs}}
    return f"```json\n{json.dumps(tool_call, ensure_ascii=False)}\n```"

# Example usage:
# sql_example = format_tool_call("sql_query", query="""
#     SELECT 
#         SUM(TOTAL_ELEC_EGY) AS conso_kwh,
#         SUM(PIECE_WEIGHT_MEAS)/1000.0 AS tonnes
#     FROM "02-EAF" e
#     JOIN "05-CCM-Brame" b ON e.HEATID = b.HEAT_STEEL_ID
# """)
# print(sql_example)

def demo_kpi_calculation():
    """
    Demonstrate proper KPI calculation with tool calls.
    This shows how to properly format tool calls for the LLM agent.
    """
    print(f"\n{Fore.YELLOW}===== KPI Calculation Demo =====")
    print(f"{Fore.CYAN}This demonstrates how to properly format tool calls for KPI calculations")
    
    # KPI 1: Consommation électrique spécifique
    print(f"\n{Fore.GREEN}KPI 1: Consommation électrique spécifique")
    print(f"{Fore.WHITE}Step 1: Query for electrical consumption data")
    kpi1_sql = format_tool_call("sql_query", query="""
        SELECT 
            (SELECT SUM(CONS_ELEC_KWH) FROM eaf) + (SELECT SUM(CONS_ELEC_KWH) FROM lf) AS conso_totale,
            (SELECT SUM(POIDS_BRAMES_T) FROM ccm) AS tonnes_produites
    """)
    print(kpi1_sql)
    
    print(f"\n{Fore.WHITE}Step 2: Calculate energy intensity with the results")
    kpi1_calc = format_tool_call("calculate_energy_intensity", 
                                conso_kwh=1234567, 
                                tonnes=45678)
    print(kpi1_calc)
    
    # KPI 2: Rendement métallurgique
    print(f"\n{Fore.GREEN}KPI 2: Rendement métallurgique")
    print(f"{Fore.WHITE}Step 1: Query for metallurgical yield data")
    kpi2_sql = format_tool_call("sql_query", query="""
        SELECT 
            SUM(p.POIDS_FERRAILLES_T) AS ferrailles_entree,
            (SELECT SUM(POIDS_BRAMES_T) FROM ccm) AS brames_sortie
        FROM paf p
    """)
    print(kpi2_sql)
    
    print(f"\n{Fore.WHITE}Step 2: Calculate metallurgical yield")
    kpi2_calc = format_tool_call("calculate_rendement", 
                                poids_brames=45678, 
                                poids_ferrailles=50000)
    print(kpi2_calc)
    
    print(f"\n{Fore.YELLOW}===== End of Demo =====")
    print(f"{Fore.WHITE}For each KPI, always follow this pattern:")
    print(f"1. Make a SQL query with proper JSON formatting")
    print(f"2. Use the results to calculate the KPI with the appropriate tool")
    print(f"3. Never mix text with the JSON tool call")
    print(f"4. Each tool call should be a separate message")
    print(f"{Fore.CYAN}{'-' * 60}\n")

# Uncomment to run the demo:
# demo_kpi_calculation()

# Print welcome message
def print_welcome():
    print(f"\n{Fore.CYAN}{'=' * 60}")
    print(f"{Fore.CYAN}||{Fore.WHITE + Style.BRIGHT}              AI ASSISTANT CHAT INTERFACE              {Fore.CYAN}||")
    print(f"{Fore.CYAN}{'=' * 60}")
    print(f"{Fore.GREEN}Type your messages below. Commands: {Fore.RED}!exit{Fore.GREEN}, {Fore.RED}!clear{Fore.GREEN}, {Fore.RED}!help")
    print(f"{Fore.CYAN}{'-' * 60}\n")

# Display help information
def print_help():
    print(f"\n{Fore.YELLOW}Available commands:")
    print(f"{Fore.RED}!exit{Fore.WHITE} - Exit the chat application")
    print(f"{Fore.RED}!clear{Fore.WHITE} - Clear the screen")
    print(f"{Fore.RED}!help{Fore.WHITE} - Show this help message")
    print(f"{Fore.RED}!reset{Fore.WHITE} - Reset the conversation history")
    print(f"{Fore.RED}!system <prompt>{Fore.WHITE} - Change the system prompt")
    print(f"{Fore.CYAN}{'-' * 60}\n")

# Clear the screen
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')
    print_welcome()

# Animated typing effect for AI responses
def print_animated(text, color=Fore.CYAN, delay=0.005):
    try:
        for char in text:
            print(f"{color}{char}", end='', flush=True)
            time.sleep(delay)
        print()
    except (KeyboardInterrupt, Exception):
        # If interrupted, just print the rest of the text immediately
        print(f"{color}{text}")

# Print a spinner while waiting for response
def show_spinner(seconds=1):
    spinner = ['|', '/', '-', '\\']
    print(f"{Fore.MAGENTA}Assistant: {Style.DIM}thinking ", end='', flush=True)
    try:
        for _ in range(seconds * 2):
            for char in spinner:
                print(f"\b{char}", end='', flush=True)
                time.sleep(0.125)
    except (KeyboardInterrupt, Exception):
        pass
    finally:
        print(f"\r{' ' * 50}\r", end='', flush=True)

print_welcome()

while True:
    try:
        message = input(f"{Fore.GREEN + Style.BRIGHT}You: {Style.RESET_ALL}")
        
        # Check for commands
        if message.lower() in ['!exit', '!quit', '!bye']:
            print(f"\n{Fore.YELLOW}Thank you for using the AI Assistant. Goodbye!")
            break
        elif message.lower() == '!clear':
            clear_screen()
            continue
        elif message.lower() == '!help':
            print_help()
            continue
        elif message.lower() == '!reset':
            chat_llm.chat_history = []
            chat_llm.messages = []
            print(f"{Fore.YELLOW}Conversation history has been reset.")
            continue
        elif message.lower().startswith('!system '):
            new_prompt = message[8:].strip()
            if new_prompt:
                chat_llm.set_system_prompt(new_prompt)
                print(f"{Fore.YELLOW}System prompt updated to: {Style.BRIGHT}{new_prompt}")
            else:
                print(f"{Fore.RED}Please provide a system prompt after !system")
            continue
        elif not message.strip():
            continue
            
        # Show thinking animation
        show_spinner(2)
        
        # Get response
        response = chat_llm.chat(message)
        
        # Print response with typing effect
        print(f"{Fore.CYAN}Assistant: ", end='')
        print_animated(response, Fore.CYAN)
        print(f"{Fore.CYAN}{'-' * 60}")
        
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}Chat session interrupted. Exiting...")
        break
    except Exception as e:
        print(f"\n{Fore.RED}Error: {str(e)}")
        print(f"{Fore.YELLOW}Continuing chat...")


