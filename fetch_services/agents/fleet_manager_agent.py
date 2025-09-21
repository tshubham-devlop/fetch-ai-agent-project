import sys
import os
import re
import requests
from datetime import datetime, time
from uagents import Agent, Context, Model, Protocol
from openai import AsyncOpenAI
from rapidfuzz import process, fuzz
from uagents.setup import fund_agent_if_low

# --- Path and Config ---
# This allows the script to find the config module when run in Docker
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(PROJECT_ROOT)
from config.settings import ASI_API_KEY, KNOWLEDGE_GRAPH_GIST_ID, AGENTVERSE_API_KEY

# --- ASI:One API Client ---
if not ASI_API_KEY or "YOUR" in ASI_API_KEY:
    print("WARNING: ASI_API_KEY not found. LLM functionality will be disabled.")
    asi_client = None
else:
    asi_client = AsyncOpenAI(api_key=ASI_API_KEY, base_url="https://api.asi1.ai/v1")

# --- Agent Definition (with Mailbox for Agentverse) ---
FLEET_MANAGER_SEED = "echonet_fleet_manager_super_secret_seed_phrase"
agent = Agent(
    name="EchoNetFleetManager",
    seed=FLEET_MANAGER_SEED,
    # The mailbox connects the agent to the Agentverse messaging network, making it public.
    mailbox=f"{AGENTVERSE_API_KEY}@agentverse.ai",
)
fund_agent_if_low(agent.wallet.address())

# --- Communication Models ---
class QueryRequest(Model):
    query: str

class QueryResponse(Model):
    answer: str

query_protocol = Protocol("FleetManagerQuery", version="1.0")

# --- Knowledge Base Logic (Fetches from Gist) ---
KNOWLEDGE_GRAPH_RAW_URL = f"https://gist.githubusercontent.com/raw/{KNOWLEDGE_GRAPH_GIST_ID}/knowledge_graph.metta"
LOCATIONS_CACHE = {}
EVENTS_CACHE = []

def load_knowledge_base():
    """Fetches the knowledge base from the public Gist URL and parses it."""
    global LOCATIONS_CACHE, EVENTS_CACHE
    print(f"Attempting to load knowledge base from public Gist...")
    try:
        response = requests.get(KNOWLEDGE_GRAPH_RAW_URL, timeout=10)
        response.raise_for_status()
        content = response.text
        
        locations = {}
        events = []
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith(";"): continue
            
            loc_match = re.match(r'\(location (\S+) "(.*)" ([\d\.\-]+) ([\d\.\-]+)\)', line)
            if loc_match:
                loc_id, name, lat, lon = loc_match.groups()
                locations[loc_id] = {"name": name, "lat": float(lat), "lon": float(lon)}
            
            event_match = re.match(r'\(noise_event (\S+) (\S+) "([^"]+)" (\d+\.?\d*)\)', line)
            if event_match:
                _, loc_id, timestamp, db = event_match.groups()
                events.append({"loc_id": loc_id, "timestamp": timestamp, "db": float(db)})
        
        LOCATIONS_CACHE = locations
        EVENTS_CACHE = events
        print(f"Successfully loaded {len(LOCATIONS_CACHE)} locations and {len(EVENTS_CACHE)} events from Gist.")
    except Exception as e:
        print(f"ERROR: Could not load knowledge base from Gist: {e}")

def get_average_db(events, loc_id, night_only=False):
    vals = []
    for ev in events:
        if ev["loc_id"] != loc_id: continue
        if night_only:
            try:
                t = datetime.fromisoformat(ev["timestamp"].rstrip('Z')).time()
                if not (time(22, 0) <= t or t < time(6, 0)): continue
            except ValueError: continue
        vals.append(ev["db"])
    return sum(vals) / len(vals) if vals else None

def generate_facts_summary(events, locations):
    lines = ["Here are the current facts about the sound environment based on validated sensor data:"]
    if not locations:
        return "No data is available in the knowledge base."
    for loc_id, loc_data in locations.items():
        avg_all = get_average_db(events, loc_id)
        avg_night = get_average_db(events, loc_id, night_only=True)
        avg_all_str = f"{avg_all:.1f} dB" if avg_all is not None else "No data"
        avg_night_str = f"{avg_night:.1f} dB" if avg_night is not None else "No data"
        lines.append(f"- The location '{loc_data['name']}' (ID: {loc_id}) has an overall average noise level of {avg_all_str} and a nighttime average of {avg_night_str}.")
    return "\n".join(lines)

async def query_llm_with_rag(user_query: str) -> str:
    if not asi_client:
        return "The ASI:One LLM is not configured."
    facts = generate_facts_summary(EVENTS_CACHE, LOCATIONS_CACHE)
    prompt = (
        f"You are the EchoNet Fleet Manager... Answer the user's query based ONLY on these facts...\n\n"
        f"--- FACTS ---\n{facts}\n\n--- USER QUERY ---\n{user_query}\n\n--- ANSWER ---\n"
    )
    try:
        response = await asi_client.chat.completions.create(
            model="asi1-extended",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error querying ASI:One LLM: {e}"

# --- Agent Logic ---
@agent.on_event("startup")
async def startup(ctx: Context):
    ctx.logger.info(f"Fleet Manager started on Agentverse. Address: {agent.address}")
    load_knowledge_base()

@agent.on_interval(period=30.0)
async def sync_knowledge_base(ctx: Context):
    ctx.logger.info("Syncing with public knowledge base Gist...")
    load_knowledge_base()

@query_protocol.on_message(model=QueryRequest, replies=QueryResponse)
async def handle_query(ctx: Context, sender: str, msg: QueryRequest):
    ctx.logger.info(f"Received query: '{msg.query}' from {sender}")
    answer = await query_llm_with_rag(msg.query)
    await ctx.send(sender, QueryResponse(answer=answer))

# --- Main Execution ---
if __name__ == "__main__":
    # FIX: The publish_manifest flag belongs on the .include() method, not the Agent constructor.
    agent.include(query_protocol, publish_manifest=True)
    agent.run()

