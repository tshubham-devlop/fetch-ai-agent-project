import os
from flask import Flask, request, jsonify
import json

# --- Path Configuration ---
# Ensure we can access config/ and other root-level modules
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)


app = Flask(__name__)

@app.route('/ingest', methods=['POST'])
def ingest_packet():
    """
    This endpoint acts as the final destination for validated data from the agent network.
    It receives an EnrichedData packet, logs it, and sends back an acknowledgment.
    """
    data = request.json
    print("\n✅ Received validated data packet from agent network:")
    print(json.dumps(data, indent=2))

    # In a real system, this is where you would save the data to a database
    # or forward it into the next stage of your processing pipeline (e.g., a real Fluence service).

    return jsonify({"status": "ACK ✅", "message": "Data ingested successfully."})

if __name__ == '__main__':
    # Running on port 5001 to avoid conflict with the main API orchestrator
    print("Starting Data Ingestion API server on http://127.0.0.1:5001")
    app.run(host='0.0.0.0', port=5001, debug=True)


    

