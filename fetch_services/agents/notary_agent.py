# Notary Agent
# This agent is responsible for maintaining the shared knowledge base.
# import sys
# import os
# import json
# import threading
# from uagents import Agent, Model, Context
# from uagents.setup import fund_agent_if_low
# from datetime import timezone
# from datetime import datetime

# # --- Path Configuration ---
# # This ensures the agent can find other project files from its location.


# BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# SENSOR_REGISTRY_FILE = os.path.join(BASE_DIR, "sensor_registry.json")
# METTA_KB_FILE =os.path.join(BASE_DIR, "knowledge_graph.metta")

# # Import the schema for the incoming message
# from schemas import FactCandidate

# # --- Agent Definition ---
# # This seed should be a well-known, constant value for the network.
# NOTARY_SEED = "notary_agent_super_secret_seed_phrase_for_echonet"
# agent = Agent(
#     name="EchoNetNotary",
#     seed=NOTARY_SEED,
#     port=8004,
#     endpoint=["http://127.0.0.1:8004/submit"],
# )

# # --- Agent State ---
# # The Notary loads the registry into its memory for quick lookups.
# SENSOR_REGISTRY = {}
# # It keeps track of which locations it has already written to the knowledge graph
# # to avoid duplicating location atoms.
# WRITTEN_LOCATIONS = set()
# # A simple counter to generate unique event IDs.
# EVENT_COUNTER = 0

# @agent.on_event("startup")
# async def startup(ctx: Context):
#     """
#     On startup, the Notary loads the sensor registry and initializes the
#     shared knowledge base file, ensuring it starts from a clean slate.
#     """
#     global SENSOR_REGISTRY, WRITTEN_LOCATIONS, EVENT_COUNTER
#     ctx.logger.info(f"Notary Agent starting up. Address: {agent.address}")
#     try:
#         with open(SENSOR_REGISTRY_FILE, 'r') as f:
#             SENSOR_REGISTRY = json.load(f)
#         ctx.logger.info(f"Successfully loaded sensor registry with {len(SENSOR_REGISTRY)} devices.")
#     except (FileNotFoundError, json.JSONDecodeError):
#         ctx.logger.warning("Sensor registry not found or is empty. Notary will only process facts for known devices.")

#     # Initialize or clear the knowledge graph file
#     with open(METTA_KB_FILE, 'w') as f:
#         f.write("; EchoNet Shared Knowledge Graph\n")
#         f.write("; Managed exclusively by the Notary Agent.\n")
    
#     WRITTEN_LOCATIONS = set()
#     EVENT_COUNTER = 0
#     ctx.logger.info(f"Knowledge base initialized at '{METTA_KB_FILE}'")

# @agent.on_message(model=FactCandidate, replies=set())
# async def add_fact_to_kb(ctx: Context, sender: str, msg: FactCandidate):
#     global WRITTEN_LOCATIONS, EVENT_COUNTER
    
#     data = msg.validated_event   # <-- unpack the actual SensorData object
#     ctx.logger.info(f"Received fact candidate from worker for device {data.mac_address}")
    
#     # 1. Look up sensor details from the in-memory registry.
#     sensor_info = SENSOR_REGISTRY.get(data.mac_address)
#     if not sensor_info:
#         ctx.logger.warning(f"Received fact for unregistered MAC address {data.mac_address}. Discarding.")
#         return

#     loc_id = sensor_info['loc_id']
    
#     with open(METTA_KB_FILE, "a") as f:
#         # 2. Location Atom Logic: Write the location atom only if it's new.
#         if loc_id not in WRITTEN_LOCATIONS:
#             f.write(f"\n; --- Location Definition: {sensor_info['name']} ---\n")
#             f.write(f"(location {loc_id} \"{sensor_info['name']}\" {sensor_info['latitude']} {sensor_info['longitude']})\n")
#             WRITTEN_LOCATIONS.add(loc_id)
#             ctx.logger.info(f"New location '{loc_id}' added to knowledge base.")

#         # 3. Noise Event Atom Logic: Always write a new event.
#         EVENT_COUNTER += 1
#         event_id = f"N{str(EVENT_COUNTER).zfill(3)}"
        
#         iso_timestamp = datetime.fromtimestamp(data.timestamp, tz=timezone.utc).isoformat()
        
#         f.write(f"(noise_event {event_id} {loc_id} \"{iso_timestamp}\" {data.sound_level_db})\n")
#         f.flush()
#         os.fsync(f.fileno())

#     ctx.logger.info(f"New noise event '{event_id}' from {loc_id} added to knowledge base.")


# if __name__ == "__main__":
#     print(f"Starting Notary Agent...")
#     print(f"Address: {agent.address}")
#     agent.run()
import sys
import os
import json
import requests
from uagents import Agent, Context
from datetime import datetime, timezone

# --- Path and Config ---
# This ensures the agent can find other project files and the config.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(PROJECT_ROOT)
# The Notary still needs the local registry to look up location details.
SENSOR_REGISTRY_FILE = os.path.join(PROJECT_ROOT, "sensor_registry.json")

# Import secrets and configuration for the Gist
from config.settings import GITHUB_PAT, KNOWLEDGE_GRAPH_GIST_ID

# Import the schema for the incoming message
from fetch_services.agents.schemas import FactCandidate

# --- Agent Definition ---
NOTARY_SEED = "notary_agent_super_secret_seed_phrase_for_echonet"
agent = Agent(
    name="EchoNetNotary",
    seed=NOTARY_SEED,
    # The port/endpoint are for local testing; on Agentverse, it will use its mailbox.
    port=8001,
    endpoint=["http://127.0.0.1:8001/submit"],
)

# --- State and Gist Helpers ---
SENSOR_REGISTRY = {}
WRITTEN_LOCATIONS = set()
EVENT_COUNTER = 0
GIST_API_URL = f"https://api.github.com/gists/{KNOWLEDGE_GRAPH_GIST_ID}"
GIST_HEADERS = {"Authorization": f"token {GITHUB_PAT}", "Accept": "application/vnd.github.v3+json"}

def update_knowledge_graph_gist(new_content: str, ctx: Context):
    """
    Atomically updates the public knowledge graph Gist by fetching its
    current content, appending the new atoms, and patching it.
    """
    try:
        # Step 1: Get the current content of the Gist file.
        response = requests.get(GIST_API_URL, headers=GIST_HEADERS, timeout=10)
        response.raise_for_status()
        # We assume the Gist has a file named 'knowledge_graph.metta'
        current_content = response.json()['files']['knowledge_graph.metta']['content']
        
        # Step 2: Append the new atoms to the current content.
        updated_content = current_content + new_content
        
        # Step 3: Send a PATCH request to update the Gist.
        payload = {"files": {"knowledge_graph.metta": {"content": updated_content}}}
        patch_response = requests.patch(GIST_API_URL, headers=GIST_HEADERS, json=payload, timeout=10)
        patch_response.raise_for_status()
        
        ctx.logger.info("Successfully updated public knowledge graph Gist.")
    except requests.exceptions.RequestException as e:
        ctx.logger.error(f"Failed to update knowledge graph Gist: {e}")
    except KeyError:
        ctx.logger.error("Gist does not contain a 'knowledge_graph.metta' file. Please check your Gist setup.")


@agent.on_event("startup")
async def startup(ctx: Context):
    """
    On startup, the Notary loads the local sensor registry and initializes the
    public knowledge base Gist, ensuring it starts from a clean slate.
    """
    global SENSOR_REGISTRY, WRITTEN_LOCATIONS, EVENT_COUNTER
    ctx.logger.info(f"Notary Agent starting up. Address: {agent.address}")
    try:
        with open(SENSOR_REGISTRY_FILE, 'r') as f:
            SENSOR_REGISTRY = json.load(f)
        ctx.logger.info(f"Successfully loaded sensor registry with {len(SENSOR_REGISTRY)} devices.")
    except (FileNotFoundError, json.JSONDecodeError):
        ctx.logger.warning("Local sensor registry not found or is empty.")

    # Initialize the public Gist with a header
    initial_content = "; EchoNet Shared Knowledge Graph\n; Managed by the Notary Agent.\n"
    update_knowledge_graph_gist(initial_content, ctx)
    
    WRITTEN_LOCATIONS = set()
    EVENT_COUNTER = 0
    ctx.logger.info("Public knowledge base Gist initialized.")

@agent.on_message(model=FactCandidate, replies=set())
async def add_fact_to_kb(ctx: Context, sender: str, msg: FactCandidate):
    """
    Receives a validated fact and writes it to the PUBLIC knowledge graph Gist.
    """
    global WRITTEN_LOCATIONS, EVENT_COUNTER
    
    data = msg.validated_event
    ctx.logger.info(f"Received fact candidate from worker for device {data.mac_address}")
    
    sensor_info = SENSOR_REGISTRY.get(data.mac_address)
    if not sensor_info:
        ctx.logger.warning(f"Received fact for unregistered MAC address {data.mac_address}. Discarding.")
        return

    loc_id = sensor_info['loc_id']
    new_atoms_to_write = ""
    
    # Location Atom Logic: Add the location atom only if it's new.
    # To be robust, we need to check the Gist content itself. For this prototype,
    # the in-memory WRITTEN_LOCATIONS is a good-enough approximation.
    if loc_id not in WRITTEN_LOCATIONS:
        new_atoms_to_write += f"\n; --- Location Definition: {sensor_info['name']} ---\n"
        new_atoms_to_write += f"(location {loc_id} \"{sensor_info['name']}\" {sensor_info['latitude']} {sensor_info['longitude']})\n"
        WRITTEN_LOCATIONS.add(loc_id)

    # Noise Event Atom Logic: Always add a new event.
    EVENT_COUNTER += 1
    event_id = f"N{str(EVENT_COUNTER).zfill(3)}"
    iso_timestamp = datetime.fromtimestamp(data.timestamp, tz=timezone.utc).isoformat()
    new_atoms_to_write += f"(noise_event {event_id} {loc_id} \"{iso_timestamp}\" {data.sound_level_db})\n"
    
    # Update the public Gist with the new atoms
    update_knowledge_graph_gist(new_atoms_to_write, ctx)

if __name__ == "__main__":
    print(f"Starting Notary Agent...")
    print(f"Address: {agent.address}")
    agent.run()



