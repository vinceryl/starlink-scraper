from flask import Flask, render_template, jsonify, send_file
import os
import traceback
from scraper import scrape_starlink

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/scrape", methods=["POST"])
def scrape():
    try:
        data, total = scrape_starlink()
        return jsonify({
            "success": True,
            "total_usage": total,
            "data": data
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/download-csv")
def download_csv():
    csv_path = "output/starlink_usage.csv"
    if os.path.exists(csv_path):
        return send_file(csv_path, as_attachment=True)
    return "CSV not found. Run a scrape first.", 404

if __name__ == "__main__":
    app.run(debug=True, port=5002)  # Changed from 5001 to avoid conflict
