# fetch_services/agents/query.py

import sys
import os
import asyncio

# --- Path Configuration (Corrected) ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from fetch_services.agents.fleet_manager_agent import QueryRequest, QueryResponse, query_protocol, FLEET_MANAGER_SEED
from uagents import Agent, Context
from uagents.crypto import Identity

# --- Agent and Address Configuration ---
FLEET_MANAGER_ADDRESS = Identity.from_seed(FLEET_MANAGER_SEED, 0).address

# FIX: Make the QueryClient a public agent so it can receive replies.
query_agent = Agent(
    name="QueryClient",
    seed="a_different_secret_seed_for_the_query_client",
    port=8008,
    # Add an endpoint so the network knows where to deliver messages
    endpoint=["http://127.0.0.1:8008/submit"],
    # Connect to the Agentverse public mailbox service
    mailbox=True,
)

# ... rest of the code is unchanged ...

query_agent.include(query_protocol)

@query_agent.on_event("startup")
async def send_query(ctx: Context):
    if len(sys.argv) < 2:
        ctx.logger.error("Usage: python fetch_services/agents/query.py \"<your question in quotes>\"")
        await query_agent.stop()
        return

    question = sys.argv[1]
    
    ctx.logger.info(f"❓ Sending query to Fleet Manager ({FLEET_MANAGER_ADDRESS}): '{question}'")
    await ctx.send(FLEET_MANAGER_ADDRESS, QueryRequest(query=question))

@query_agent.on_message(model=QueryResponse)
async def handle_response(ctx: Context, sender: str, msg: QueryResponse):
    ctx.logger.info(f"Received answer from agent {sender}:")
    print(f"🤖 Fleet Manager says: \"{msg.answer}\"")
    await query_agent.stop()

if __name__ == "__main__":
    query_agent.run()