
# import sys
# import os
# import re
# import math
# from datetime import datetime, time
# from uagents import Agent, Context, Model, Protocol
# from openai import AsyncOpenAI
# from rapidfuzz import process, fuzz
# from uagents.setup import fund_agent_if_low

# # --- Path Configuration ---
# PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# sys.path.append(PROJECT_ROOT)
# KNOWLEDGE_BASE_FILE = os.path.join(PROJECT_ROOT,"knowledge_graph.metta")
# from config.settings import GITHUB_PAT, KNOWLEDGE_GRAPH_GIST_ID
# from config.settings import ASI_API_KEY, AGENTVERSE_API_KEY

# # --- ASI:One API Configuration ---
# if not ASI_API_KEY or "YOUR" in ASI_API_KEY:
#     print("WARNING: ASI_API_KEY not found or not configured. LLM functionality will be disabled.")
#     asi_client = None
# else:
#     asi_client = AsyncOpenAI(api_key=ASI_API_KEY, base_url="https://api.asi1.ai/v1")

# # --- Agent Definition ---
# FLEET_MANAGER_SEED = "echonet_fleet_manager_super_secret_seed_phrase"
# agent = Agent(
#     name="EchoNetFleetManager",
#     seed=FLEET_MANAGER_SEED,
#     port=8000,
#     endpoint=["http://127.0.0.1:8000/submit"],
# )
# fund_agent_if_low(agent.wallet.address())

# # --- Communication Models ---
# class QueryRequest(Model):
#     query: str

# class QueryResponse(Model):
#     answer: str

# query_protocol = Protocol("FleetManagerQuery", version="1.0")

# # --- Knowledge Base Parsing & Helper Functions ---
# LOCATIONS_CACHE = {}
# EVENTS_CACHE = []

# def load_knowledge_base():
#     """
#     Parses the .metta file and provides detailed debug output at each step.
#     """
#     global LOCATIONS_CACHE, EVENTS_CACHE
#     locations = {}
#     events = []
#     print("\n--- DEBUG: Starting Knowledge Base Load ---")
#     if not os.path.exists(KNOWLEDGE_BASE_FILE):
#         print(f"DEBUG: Knowledge base file not found at '{KNOWLEDGE_BASE_FILE}'")
#         return

#     with open(KNOWLEDGE_BASE_FILE, 'r') as f:
#         print("DEBUG: Reading file line by line...")
#         for i, line in enumerate(f):
#             line = line.strip()
#             print(f"  - Line {i+1}: '{line}'")
#             if not line or line.startswith(";"):
#                 print("     -> Skipping comment or empty line.")
#                 continue
            
#             # Attempt to match a location atom
#             loc_match = re.match(r'\(location (\S+) "(.*)" ([\d\.\-]+) ([\d\.\-]+)\)', line)
#             if loc_match:
#                 loc_id, name, lat, lon = loc_match.groups()
#                 locations[loc_id] = {"name": name, "lat": float(lat), "lon": float(lon)}
#                 print(f"     -> MATCHED Location: ID={loc_id}, Name='{name}'")
#                 continue
            
#             # Attempt to match a noise event atom
#             event_match = re.match(r'\(noise_event (\S+) (\S+) "([^"]+)" (\d+\.?\d*)\)', line)
#             if event_match:
#                 _, loc_id, timestamp, db = event_match.groups()
#                 events.append({"loc_id": loc_id, "timestamp": timestamp, "db": float(db)})
#                 print(f"     -> MATCHED Noise Event: Location ID={loc_id}, DB={db}")
#                 continue
            
#             print("     -> NO MATCH FOUND for this line.")

#     LOCATIONS_CACHE = locations
#     EVENTS_CACHE = events
#     print("\nDEBUG: Knowledge Base Loading Complete.")
#     print(f"  - Found {len(LOCATIONS_CACHE)} unique locations.")
#     print(f"  - Found {len(EVENTS_CACHE)} noise events.")
#     print("--- END KB Load ---\n")


# def get_average_db(events, loc_id, night_only=False):
#     """
#     FIX: This function now correctly calculates the average decibel level
#     for a given location from the list of event facts.
#     """
#     vals = []
#     for ev in events:
#         # Check if the event belongs to the location we're interested in
#         if ev["loc_id"] != loc_id:
#             continue
        
#         # If the night_only flag is true, filter out daytime events
#         if night_only:
#             try:
#                 # Parse the ISO timestamp and check if the time is within the night range (10 PM to 6 AM)
#                 t = datetime.fromisoformat(ev["timestamp"].rstrip('Z')).time()
#                 if not (time(22, 0) <= t or t < time(6, 0)):
#                     continue
#             except ValueError:
#                 # Handle cases where the timestamp might be malformed
#                 continue
        
#         vals.append(ev["db"])
        
#     # Return the average if we have values, otherwise return None
#     return sum(vals) / len(vals) if vals else None

# def find_location_by_name(user_input: str, locations: dict):
#     # ... (this function is unchanged)
#     return None

# def generate_facts_summary(events, locations):
#     """Creates a plain-text summary of the knowledge base to be used as context for the LLM."""
#     print("--- DEBUG: Generating Facts Summary ---")
#     lines = ["Here are the current facts about the sound environment based on validated sensor data:"]
#     if not locations:
#         print("  - No locations found in cache. Summary will be empty.")
#         return "No data is available in the knowledge base."

#     for loc_id, loc_data in locations.items():
#         avg_all = get_average_db(events, loc_id)
#         avg_night = get_average_db(events, loc_id, night_only=True)
#         avg_all_str = f"{avg_all:.1f} dB" if avg_all is not None else "No data"
#         avg_night_str = f"{avg_night:.1f} dB" if avg_night is not None else "No data"
#         line = f"- The location '{loc_data['name']}' (ID: {loc_id}) has an overall average noise level of {avg_all_str} and a nighttime average of {avg_night_str}."
#         print(f"  - Adding fact: {line}")
#         lines.append(line)
    
#     summary = "\n".join(lines)
#     print("--- END Facts Summary ---\n")
#     return summary


# async def query_llm_with_rag(user_query: str) -> str:
#     """Performs the RAG process with detailed debug output."""
#     if not asi_client:
#         return "The ASI:One LLM is not configured. Please set the API key."

#     # 1. RETRIEVE facts from our knowledge base cache
#     facts = generate_facts_summary(EVENTS_CACHE, LOCATIONS_CACHE)
    
#     # 2. AUGMENT the prompt with the retrieved facts
#     prompt = (
#         f"You are the EchoNet Fleet Manager... Answer the user's query based ONLY on these facts...\n\n"
#         f"--- FACTS ---\n{facts}\n\n--- USER QUERY ---\n{user_query}\n\n--- ANSWER ---\n"
#     )
    
#     print("--- DEBUG: Full Prompt being sent to ASI:One LLM ---")
#     print(prompt)
#     print("--- END Prompt ---")
    
#     # 3. GENERATE the final answer using the LLM
#     try:
#         response = await asi_client.chat.completions.create(
#             model="asi1-extended",
#             messages=[{"role": "user", "content": prompt}],
#             temperature=0.2,
#         )
#         return response.choices[0].message.content
#     except Exception as e:
#         return f"Error querying ASI:One LLM: {e}"


# # --- Agent Logic ---
# @agent.on_event("startup")
# async def startup(ctx: Context):
#     ctx.logger.info(f"Fleet Manager started. Address: {agent.address}")
#     load_knowledge_base()

# @agent.on_interval(period=15.0)
# async def sync_knowledge_base(ctx: Context):
#     ctx.logger.info("Syncing with shared knowledge base...")
#     load_knowledge_base()

# @query_protocol.on_message(model=QueryRequest, replies=QueryResponse)
# async def handle_query(ctx: Context, sender: str, msg: QueryRequest):
#     """Handles incoming natural language queries from users or other agents."""
#     ctx.logger.info(f"Received query: '{msg.query}'")
#     answer = await query_llm_with_rag(msg.query)
#     await ctx.send(sender, QueryResponse(answer=answer))


# # --- Main Execution ---
# if __name__ == "__main__":
#     agent.include(query_protocol, publish_manifest=True)
#     print(PROJECT_ROOT)
#     agent.run()

import sys
import os
import re
import requests
from datetime import datetime, time
from uagents import Agent, Context, Model, Protocol
from openai import AsyncOpenAI
from uagents.setup import fund_agent_if_low

# --- Path and Config ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(PROJECT_ROOT)
from config.settings import ASI_API_KEY, KNOWLEDGE_GRAPH_GIST_ID, AGENTVERSE_API_KEY

# --- ASI:One API Client ---
asi_client = None
if ASI_API_KEY and "YOUR" not in ASI_API_KEY:
    asi_client = AsyncOpenAI(api_key=ASI_API_KEY, base_url="https://api.asi1.ai/v1")

# --- Fleet Manager Seed & Agent ---
FLEET_MANAGER_SEED = "echonet_fleet_manager_super_secret_seed_phrase"
agent = Agent(
    name="EchoNetFleetManager",
    seed=FLEET_MANAGER_SEED,
    port=8000,
    endpoint=["http://127.0.0.1:8000/submit"],
    # mailbox=f"{AGENTVERSE_API_KEY}@agentverse.ai",  # enables public messaging
    mailbox=True,
    publish_agent_details=True,
)
fund_agent_if_low(agent.wallet.address())

# --- Communication Models ---
class QueryRequest(Model):
    query: str

class QueryResponse(Model):
    answer: str

query_protocol = Protocol("FleetManagerQuery", version="1.0")

# --- Knowledge Base ---
KNOWLEDGE_GRAPH_RAW_URL = f"https://gist.githubusercontent.com/raw/{KNOWLEDGE_GRAPH_GIST_ID}/knowledge_graph.metta"
LOCATIONS_CACHE = {}
EVENTS_CACHE = []

def load_knowledge_base():
    global LOCATIONS_CACHE, EVENTS_CACHE
    print(f"\n=== DEBUG: Loading knowledge base from: {KNOWLEDGE_GRAPH_RAW_URL}")
    try:
        r = requests.get(KNOWLEDGE_GRAPH_RAW_URL, timeout=10)
        r.raise_for_status()
        content = r.text

        locations, events = {}, []
        for i, line in enumerate(content.splitlines()):
            line = line.strip()
            if not line or line.startswith(";"):
                continue
            # print(f"  Line {i+1}: {line}")

            loc_match = re.match(r'\(location (\S+) "(.*)" ([\d\.\-]+) ([\d\.\-]+)\)', line)
            if loc_match:
                loc_id, name, lat, lon = loc_match.groups()
                locations[loc_id] = {"name": name, "lat": float(lat), "lon": float(lon)}
                # print(f"    -> Matched Location: {locations[loc_id]}")
            event_match = re.match(r'\(noise_event (\S+) (\S+) "([^"]+)" (\d+\.?\d*)\)', line)
            if event_match:
                _, loc_id, timestamp, db = event_match.groups()
                events.append({"loc_id": loc_id, "timestamp": timestamp, "db": float(db)})
                # print(f"    -> Matched Noise Event: {events[-1]}")

        LOCATIONS_CACHE = locations
        EVENTS_CACHE = events
        # print(f"=== DEBUG: Loaded {len(LOCATIONS_CACHE)} locations, {len(EVENTS_CACHE)} events ===\n")
    except Exception as e:
        print(f"❌ Failed to load knowledge base: {e}")

def get_average_db(events, loc_id, night_only=False):
    vals = []
    for ev in events:
        if ev["loc_id"] != loc_id:
            continue
        if night_only:
            try:
                t = datetime.fromisoformat(ev["timestamp"].rstrip('Z')).time()
                if not (time(22,0) <= t or t < time(6,0)):
                    continue
            except Exception as e:
                print(f"⚠️ Timestamp parse error: {e}")
                continue
        vals.append(ev["db"])
    return sum(vals)/len(vals) if vals else None

def generate_facts_summary(events, locations):
    print("\n=== DEBUG: Generating Facts Summary ===")
    lines = ["Facts about the noise environment:"]
    if not locations:
        print("  -> No locations found.")
        return "No data available."
    for loc_id, loc in locations.items():
        avg_all = get_average_db(events, loc_id)
        avg_night = get_average_db(events, loc_id, night_only=True)
        avg_all_str = f"{avg_all:.1f} dB" if avg_all else "No data"
        avg_night_str = f"{avg_night:.1f} dB" if avg_night else "No data"
        fact_line = f"- '{loc['name']}' (ID: {loc_id}) avg: {avg_all_str}, night avg: {avg_night_str}"
        print(f"  -> {fact_line}")
        lines.append(fact_line)
    return "\n".join(lines)

async def query_llm_with_rag(user_query: str) -> str:
    print(f"\n=== DEBUG: Processing Query ===")
    print(f"  User Query: {user_query}")
    if not asi_client:
        return "LLM not configured (ASI API key missing)"
    facts = generate_facts_summary(EVENTS_CACHE, LOCATIONS_CACHE)
    prompt = f"Facts:\n{facts}\n\nQuery: {user_query}\nAnswer concisely:"
    print(f"  -> Full Prompt:\n{prompt}")
    try:
        resp = await asi_client.chat.completions.create(
            model="asi1-extended",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        answer = resp.choices[0].message.content
        print(f"  -> LLM Answer: {answer}")
        return answer
    except Exception as e:
        print(f"❌ LLM error: {e}")
        return f"LLM error: {e}"

# --- Agent Event Handlers ---
@agent.on_event("startup")
async def startup(ctx: Context):
    ctx.logger.info(f"Fleet Manager started at {agent.address}")
    load_knowledge_base()

@agent.on_interval(period=30.0)
async def sync_kb(ctx: Context):
    ctx.logger.info("Syncing knowledge base...")
    load_knowledge_base()

@query_protocol.on_message(model=QueryRequest, replies=QueryResponse)
async def handle_query(ctx: Context, sender: str, msg: QueryRequest):
    ctx.logger.info(f"Received query from {sender}: {msg.query}")
    print(f"=== DEBUG: Incoming Query ===\n  From: {sender}\n  Query: {msg.query}")
    answer = await query_llm_with_rag(msg.query)
    print(f"=== DEBUG: Sending Response ===\n  To: {sender}\n  Answer: {answer}")
    await ctx.send(sender, QueryResponse(answer=answer))

# --- Run Agent ---
if __name__ == "__main__":
    print(f"=== DEBUG: Starting Fleet Manager Agent ===")
    print(f"  Address: {agent.address}")
    agent.include(query_protocol, publish_manifest=True)
    agent.run()
