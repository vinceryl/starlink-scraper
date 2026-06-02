import os
import threading
from flask import Flask, render_template, jsonify, send_file
from scraper import scrape_starlink_live, save_csv, OUTPUT_CSV

app = Flask(__name__)

scrape_status = {"running": False, "message": "Nexus Standby", "done": False, "error": None}
scraped_data = []

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/scrape", methods=["POST"])
def start_scrape():
    global scrape_status, scraped_data
    if scrape_status["running"]: return jsonify({"error": "Uplink Busy"}), 400
    
    def run():
        global scrape_status, scraped_data
        scrape_status = {"running": True, "message": "Initializing...", "done": False, "error": None}
        try:
            scraped_data = scrape_starlink_live(status_callback=lambda m: scrape_status.update({"message": m}))
            save_csv(scraped_data)
            scrape_status.update({"running": False, "done": True, "message": "Telemetry Synced."})
        except Exception as e:
            scrape_status.update({"running": False, "done": True, "error": str(e)})

    threading.Thread(target=run, daemon=True).start()
    return jsonify({"status": "initiated"})

@app.route("/api/status")
def get_status(): return jsonify(scrape_status)

@app.route("/api/data")
def get_data():
    if not scraped_data: return jsonify({"data": [], "stats": {"total": "0.00 GB", "avg": "0.00 GB", "peak": "0.00 GB"}})
    
    vals = [float(row['data_usage'].split()[0]) for row in scraped_data]
    stats = {
        "total": f"{sum(vals):.2f} GB",
        "avg": f"{(sum(vals)/len(vals)):.2f} GB" if vals else "0.00",
        "peak": f"{max(vals):.2f} GB" if vals else "0.00"
    }
    return jsonify({"data": scraped_data, "stats": stats})

@app.route("/api/download")
def download(): return send_file(OUTPUT_CSV, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True, port=5000)