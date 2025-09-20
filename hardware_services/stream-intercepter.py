from flask import Flask, Response
import requests
import csv
import os

app = Flask(__name__)

SOURCE_URL = "http://192.168.185.62:5007/stream"
CSV_FILE = "stream_data.csv"

# --- Ensure CSV file has headers ---
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, mode="w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["value", "mac_address", "timestamp"])
        writer.writeheader()

@app.route("/")
def index():
    return "Stream Intercepter is running!"

@app.route("/listen")
def listen():
    def generate():
        with requests.get(SOURCE_URL, stream=True) as r:
            for line in r.iter_lines():
                if line:
                    decoded = line.decode("utf-8").replace("data: ", "")
                    print(f"[INTERCEPTER] {decoded}", flush=True)

                    # Try parsing JSON-like dict string safely
                    try:
                        data = eval(decoded)  # ⚠️ For production, use `json.loads`
                        with open(CSV_FILE, mode="a", newline="") as f:
                            writer = csv.DictWriter(f, fieldnames=["value", "mac_address", "timestamp"])
                            writer.writerow(data)
                    except Exception as e:
                        print(f"[ERROR] Could not write to CSV: {e}")

                    yield f"data: {decoded}\n\n"
    return Response(generate(), mimetype="text/event-stream")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)
