import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import time
import pandas as pd
import os
import re
import traceback
from datetime import datetime

TARGET_URL = "https://starlink.com/account/service-line/AST-2293597-46342-54?selectedDevice=ut01000000-00000000-0060d786&page=0&limit=5"

MONTH_MAP = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
}

def infer_year(month_str, ref_year, ref_month):
    m = MONTH_MAP.get(month_str[:3])
    if not m:
        return ref_year
    return ref_year - 1 if m > ref_month else ref_year

def find_bars(driver):
    """Try multiple selectors to find chart bar elements."""
    selectors = [
        "rect.MuiBarElement-root",       # MUI v5 bar chart
        "rect[class*='BarElement']",      # MUI partial class
        "rect[aria-label]",               # any rect with aria-label
        "g.recharts-bar-rectangle rect", # Recharts
        "rect.bar",                       # generic
        ".chart-bar",                     # generic class
        "rect[role='img']",
        "rect[tabindex]",
    ]
    for sel in selectors:
        bars = driver.find_elements(By.CSS_SELECTOR, sel)
        if bars:
            print(f"    [bars found with selector: {sel}  count={len(bars)}]")
            return bars, sel
    return [], None

def parse_aria_bars(driver):
    """Parse bars that have aria-label with date+GB info."""
    now = datetime.now()
    bars, sel = find_bars(driver)
    results = []
    for bar in bars:
        label = bar.get_attribute("aria-label") or ""
        if "GB" not in label:
            continue
        match = re.search(r"([A-Z][a-z]{2})\s+(\d{1,2})[^0-9]*(\d+\.?\d*)\s*GB", label)
        if not match:
            continue
        m_str, d_str, gb_str = match.groups()
        if m_str not in MONTH_MAP:
            continue
        year = infer_year(m_str, now.year, now.month)
        date_iso = f"{year}-{MONTH_MAP[m_str]:02d}-{int(d_str):02d}"
        results.append({"Date": date_iso, "Usage_GB": float(gb_str)})
    return results

def hover_and_read_tooltip(driver, bar, actions):
    """
    Hover over a bar element and read the tooltip that appears.
    Returns (date_str, gb_float) or None.
    """
    try:
        actions.move_to_element(bar).perform()
        time.sleep(0.3)

        # Try common tooltip/popover selectors
        tooltip_selectors = [
            "[class*='tooltip']",
            "[class*='Tooltip']",
            "[class*='popover']",
            "[class*='MuiChartsTooltip']",
            "[class*='recharts-tooltip']",
            ".MuiChartsTooltip-root",
            "[role='tooltip']",
        ]
        tooltip_text = ""
        for tsel in tooltip_selectors:
            tips = driver.find_elements(By.CSS_SELECTOR, tsel)
            for tip in tips:
                t = tip.text.strip()
                if t and len(t) > 3:
                    tooltip_text = t
                    break
            if tooltip_text:
                break

        if not tooltip_text:
            return None

        # Parse "Nov 30\nResidential Data  22 GB"
        now = datetime.now()
        date_match = re.search(r"([A-Z][a-z]{2})\s+(\d{1,2})", tooltip_text)
        gb_match = re.search(r"(\d+\.?\d*)\s*GB", tooltip_text)
        if date_match and gb_match:
            m_str, d_str = date_match.groups()
            gb_val = float(gb_match.group(1))
            if m_str in MONTH_MAP:
                year = infer_year(m_str, now.year, now.month)
                date_iso = f"{year}-{MONTH_MAP[m_str]:02d}-{int(d_str):02d}"
                return date_iso, gb_val
    except Exception:
        pass
    return None

def scrape_tab(driver, seen_dates):
    """Scrape current tab using aria-labels first, then hover fallback."""
    # Method 1: aria-label (fast, accurate)
    rows = parse_aria_bars(driver)
    if rows:
        added = 0
        for row in rows:
            d = row["Date"]
            if d not in seen_dates or row["Usage_GB"] > seen_dates[d]["Usage_GB"]:
                seen_dates[d] = row
                added += 1
        print(f"    [aria-label] {len(rows)} bars → {added} dates added/updated.")
        return added

    # Method 2: hover each bar and read tooltip
    print("    [no aria-labels found, trying hover tooltips...]")
    bars, sel = find_bars(driver)
    if not bars:
        print("    [no bars found with any selector — logging page source snippet]")
        # Log a snippet of page source to help diagnose
        src = driver.page_source
        # Find anything that looks like a chart SVG
        snippet_match = re.search(r"<svg[^>]*chart[^>]*>(.{0,500})", src, re.IGNORECASE)
        if snippet_match:
            print(f"    [SVG snippet: {snippet_match.group(0)[:300]}]")
        else:
            print("    [No SVG with 'chart' found in page source]")
            # Show all rect elements
            rects = driver.find_elements(By.TAG_NAME, "rect")
            print(f"    [Total <rect> elements on page: {len(rects)}]")
            for r in rects[:5]:
                print(f"       rect class='{r.get_attribute('class')}' aria='{r.get_attribute('aria-label')}'")
        return 0

    actions = ActionChains(driver)
    added = 0
    for bar in bars:
        result = hover_and_read_tooltip(driver, bar, actions)
        if result:
            date_iso, gb_val = result
            if date_iso not in seen_dates or gb_val > seen_dates[date_iso]["Usage_GB"]:
                seen_dates[date_iso] = {"Date": date_iso, "Usage_GB": gb_val}
                added += 1
    print(f"    [hover] {len(bars)} bars → {added} dates added/updated.")
    return added

def get_tab_buttons(driver):
    """Find all month-tab buttons in the chart."""
    selectors = [
        "button.MuiTab-root",
        "button[role='tab']",
        ".MuiTabs-root button",
        "[class*='MuiTab'] button",
        "[class*='tabs'] button",
    ]
    for sel in selectors:
        btns = driver.find_elements(By.CSS_SELECTOR, sel)
        if btns:
            result = [(b.text.strip(), b) for b in btns if b.text.strip()]
            if result:
                print(f"    [tabs found with selector: {sel}]")
                return result

    # Fallback: any button matching month pattern
    all_btns = driver.find_elements(By.TAG_NAME, "button")
    result = []
    for btn in all_btns:
        t = btn.text.strip()
        if re.match(r"^[A-Z][a-z]{2}(\s*[\-–—]\s*[A-Z][a-z]{2})?$", t):
            result.append((t, btn))
    if result:
        print(f"    [tabs found via button text scan]")
    return result

def get_bar_snapshot(driver):
    bars, _ = find_bars(driver)
    return frozenset(
        (b.get_attribute("aria-label") or "") + str(b.rect)
        for b in bars
    )

def scrape_starlink():
    driver = None

    try:
        options = uc.ChromeOptions()
        options.add_argument("--start-maximized")

        print(">>> Initializing Chrome...")
        try:
            driver = uc.Chrome(options=options)
        except Exception as e:
            print(f">>> Auto-detect failed: {e}, trying version_main=136...")
            driver = uc.Chrome(options=options, version_main=136)
        print(">>> Chrome launched.")

        wait = WebDriverWait(driver, 120)

        # LOGIN
        driver.get("https://www.starlink.com/account/login")
        print(">>> Please log in manually in the Chrome window.")
        wait.until(EC.url_contains("/account/home"))
        print(">>> Login confirmed!")
        time.sleep(3)

        # NAVIGATE TO USAGE PAGE
        print(">>> Navigating to usage page...")
        driver.get(TARGET_URL)

        # Wait for page to have ANY rect element (chart may use different classes)
        print(">>> Waiting for chart to render...")
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "svg")))
        driver.execute_script("window.scrollTo(0, 500);")
        time.sleep(30)  # Extra time for chart JS to fully render

        # GET LIVE TOTAL (from "Total Data Usage" heading)
        live_total = "N/A"
        try:
            # Try to find the GB value near "Total Data Usage" text
            total_els = driver.find_elements(By.XPATH, "//*[contains(text(), 'GB')]")
            for el in total_els:
                t = el.text.strip()
                if re.match(r"^\d+\.?\d*\s*GB$", t):
                    live_total = t
                    break
            print(f">>> Live total: {live_total}")
        except Exception as e:
            print(f">>> Could not get live total: {e}")

        # DISCOVER TABS
        print(">>> Discovering tab buttons...")
        tab_buttons = get_tab_buttons(driver)
        print(f">>> Found {len(tab_buttons)} tab(s):")
        for label, _ in tab_buttons:
            print(f"    '{label}'")

        if not tab_buttons:
            print(">>> ERROR: No tabs found. Scraping current view only.")
            seen_dates = {}
            scrape_tab(driver, seen_dates)
        else:
            seen_dates = {}
            for label, btn in tab_buttons:
                print(f">>> Clicking tab: '{label}'")
                try:
                    before = get_bar_snapshot(driver)
                    driver.execute_script("arguments[0].click();", btn)

                    # Wait up to 15s for chart to update
                    changed = False
                    for _ in range(15):
                        time.sleep(1)
                        if get_bar_snapshot(driver) != before:
                            changed = True
                            break

                    if not changed:
                        print(f"    Bars unchanged (first tab or already active). Parsing anyway.")
                    else:
                        time.sleep(1.5)

                    scrape_tab(driver, seen_dates)

                except Exception as e:
                    print(f"    Tab '{label}' error: {e}")
                    traceback.print_exc()

        # SAVE CSV
        if not seen_dates:
            print(">>> WARNING: No data collected.")
            driver.quit()
            return [], live_total

        final_rows = sorted(seen_dates.values(), key=lambda r: r["Date"])
        df = pd.DataFrame(final_rows)[["Date", "Usage_GB"]]
        os.makedirs("output", exist_ok=True)
        df.to_csv("output/starlink_usage.csv", index=False)
        print(f">>> SUCCESS: {len(df)} rows saved to output/starlink_usage.csv")

        driver.quit()
        return final_rows, live_total

    except Exception as e:
        print(f">>> FATAL ERROR: {e}")
        traceback.print_exc()
        try:
            if driver:
                driver.quit()
        except Exception:
            pass
        raise


if __name__ == "__main__":
    data, total = scrape_starlink()
    print(f"\nTotal: {total}")
    print(f"Rows collected: {len(data)}")
    for row in data[:10]:
        print(row)