# 📡 Reylie Starlink Scraper

A web-based tool that logs into your Starlink account, scrapes your daily data usage from the chart, and exports it as a CSV file.

---

## 📁 Project Structure

```
reylie-scraper/
├── classmate-version/
│   ├── app.py              ← Flask web server (runs on port 5002)
│   ├── scraper.py          ← Selenium scraper logic
│   ├── templates/
│   │   └── index.html      ← Web UI
│   └── output/             ← CSV files saved here after scraping
```

---

## ✅ Requirements

- Python 3.9 or higher
- Google Chrome browser (must be installed)
- Internet connection

---

## ⚙️ Installation

### Step 1 — Open PowerShell and go to the project folder

```powershell
cd C:\Users\YourName\Downloads\reylie-scraper\classmate-version
```

### Step 2 — Allow scripts to run (first time only)

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Step 3 — Create a virtual environment

```powershell
python -m venv venv
```

### Step 4 — Activate the virtual environment

```powershell
venv\Scripts\activate
```

You should see `(venv)` at the start of your terminal prompt.

### Step 5 — Install dependencies

```powershell
pip install Flask undetected-chromedriver pandas setuptools
```

---

## 🚀 Running the App

### Step 1 — Start the server

```powershell
python app.py
```

You should see:
```
* Running on http://127.0.0.1:5002
```

### Step 2 — Open your browser

Go to: **http://127.0.0.1:5002**

### Step 3 — Run the scrape

1. Click **▶ START SYNC** in the browser
2. A Chrome window will open automatically
3. Select the three dots in the right side for the sign in 
4. Log in to your Starlink account manually
  **Username:** fundamentalssystem@gmail.com
  **Password:** systemfundamentals2026
5. Wait 2–3 minutes for the scraper to collect data
6. Results will appear in the table on the page

### Step 4 — Download your data

Click **⬇ EXPORT CSV** to download your usage data as a spreadsheet.
The CSV is also saved automatically to the `output/` folder.

---