import os
import json
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)
region = os.getenv("REGION", "unknown")

def enrich_data(raw_data):
    try:
        data = json.loads(raw_data)
    except Exception as e:
        print("Error parsing data:", e)
        return None
    enriched_data = data.copy()
    enriched_data["processed_timestamp"] = datetime.utcnow().isoformat() + "Z"
    enriched_data["region"] = region
    enriched_data["custom_metadata"] = "Additional info"
    return enriched_data

@app.route('/process', methods=['POST'])
def process():
    raw_data = request.get_data(as_text=True)
    enriched = enrich_data(raw_data)
    if enriched:
        print("Processed data:", enriched)
        return jsonify(enriched), 200
    return "Error processing data", 400

if __name__ == "__main__":
    # Run the Flask app so the container can process incoming data
    app.run(host='0.0.0.0', port=5000)
