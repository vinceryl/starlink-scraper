import os
import csv
import json
import re
import datetime
import time
from playwright.sync_api import sync_playwright

# ASSIGNMENT CREDENTIALS
EMAIL = "fundamentalssystem@gmail.com"
PASSWORD = "systemfundamentals2026"
OUTPUT_CSV = "starlink_data_usage.csv"

def log(msg, callback=None):
    t = datetime.datetime.now().strftime('%H:%M:%S')
    print(f"[{t}] {msg}")
    if callback: callback(msg)

def scrape_starlink_live(status_callback=None):
    results = []
    
    with sync_playwright() as p:
        log("🛰️ Launching Stealth Chromium...", status_callback)
        browser = p.chromium.launch(headless=False, args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage"
        ])
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        # Hides automation signature
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
        page = context.new_page()

        try:
            log("Navigating to Starlink Account...", status_callback)
            page.goto("https://www.starlink.com/account", wait_until="domcontentloaded", timeout=60000)

            # --- LOGIN FLOW ---
            log("Injecting Credentials...", status_callback)
            page.wait_for_selector('input[type="email"]', timeout=15000)
            page.fill('input[type="email"]', EMAIL)
            page.click("button:has-text('Next'), button[type='submit']")
            
            time.sleep(3)
            page.wait_for_selector('input[type="password"]', timeout=10000)
            page.fill('input[type="password"]', PASSWORD)
            page.keyboard.press("Enter")

            log("⚠️ ACTION: Enter 2FA Code in Chrome window!", status_callback)
            page.wait_for_url("**/account/**", timeout=0) # Wait indefinitely for user to finish login
            
            log("✅ Handshake Confirmed. Accessing Subscriptions...", status_callback)
            page.goto("https://www.starlink.com/account/subscriptions", wait_until="domcontentloaded")
            time.sleep(5)

            # --- NAVIGATION TO GRAPH ---
            log("Opening active service line...", status_callback)
            try:
                sub_row = page.locator("text=SL Val").first
                if not sub_row.is_visible(): sub_row = page.locator("text=Active").first
                sub_row.click()
            except:
                log("⚠️ Navigation error, attempting direct path...", status_callback)
                page.goto("https://www.starlink.com/account/data-usage")

            time.sleep(5)

            # --- MULTI-MONTH SCRAPING LOOP ---
            target_months = ["Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May - Jun"]
            
            for month_name in target_months:
                log(f"Scraping telemetry for: {month_name}", status_callback)
                try:
                    month_tab = page.locator(f"text={month_name}").first
                    if month_tab.is_visible():
                        month_tab.click()
                        time.sleep(4)
                        
                        # Extract data from SVG bars
                        page.wait_for_selector('rect.MuiBarElement-root', timeout=10000)
                        bar_data = page.evaluate("""
                            () => Array.from(document.querySelectorAll('rect.MuiBarElement-series-y_0, rect.MuiBarElement-root'))
                                       .map(b => parseFloat(b.getAttribute('height') || '0'))
                        """)
                        
                        # Set start date for calibration
                        date_map = {"Nov": (2025, 11), "Dec": (2025, 12), "Jan": (2026, 1), 
                                    "Feb": (2026, 2), "Mar": (2026, 3), "Apr": (2026, 4), "May - Jun": (2026, 5)}
                        y, m = date_map.get(month_name, (2026, 5))
                        start_date = datetime.date(y, m, 1)
                        
                        # Calibration: 130 height = 0GB, axis at 43 = 20GB
                        pixel_per_gb = (130.0 - 43.1346) / 20.0

                        for i, height in enumerate(bar_data):
                            gb = round(height / pixel_per_gb, 2)
                            bar_date = start_date + datetime.timedelta(days=i)
                            
                            if bar_date <= datetime.date.today():
                                results.append({
                                    "day": bar_date.strftime("%Y-%m-%d"),
                                    "data_usage": f"{gb} GB",
                                    "extra": f" | {month_name}"
                                })
                except Exception as e:
                    log(f"⚠️ Month {month_name} skipped: {str(e)}", status_callback)

            # --- FALLBACK ---
            if not results:
                log("Live stream empty. Checking local Starlink.html backup...", status_callback)
                if os.path.exists("Starlink.html"):
                    with open("Starlink.html", "r", encoding="utf-8") as f:
                        html = f.read()
                    match = re.search(r'"dailyUsage"\s*:\s*(\[.*?\])', html, re.DOTALL)
                    if match:
                        records = json.loads(match.group(1))
                        for r in records:
                            results.append({
                                "day": r.get("date", r.get("day", "Unknown")),
                                "data_usage": f"{r.get('totalGB', r.get('usage', 0))} GB",
                                "extra": "Offline Backup"
                            })

            log(f"Extraction Successful: {len(results)} days recorded.", status_callback)
            return results

        except Exception as e:
            log(f"Uplink Fault: {str(e)}", status_callback)
            raise e
        finally:
            browser.close()

def save_csv(data):
    if not data: return
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["day", "data_usage", "extra"])
        writer.writeheader()
        writer.writerows(data)