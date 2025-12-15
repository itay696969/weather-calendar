import requests
import os
import time
import random
import subprocess
from datetime import datetime, timedelta, timezone
from requests.exceptions import ReadTimeout, RequestException

# ===== CONFIG =====

LAT_LON = {
    "צ": (32.7940, 34.9896),   # צפון
    "מ": (32.0853, 34.7818),   # מרכז
    "ד": (31.252973, 34.791462),  # דרום
    "י": (31.7683, 35.2137),   # ירושלים
}

START_HOUR = 8
END_HOUR = 19

ICS_FILE = "weather.ics"
SUMMARY_FILE = "summary.txt"

BOOTSTRAP_DAYS = 90

MAX_RETRIES = 4
BACKOFFS = [0.5, 1, 2, 4]

MIN_SLEEP = 5
MAX_SLEEP = 35

# ===== HELPERS =====

def log(msg: str):
    print(msg)
    with open(SUMMARY_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def fetch_rain_status(lat, lon, date_str, bootstrap):
    """
    מחזיר:
    True  -> ירד גשם
    False -> לא ירד גשם
    None  -> אין נתונים (⚪)
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "precipitation",
        "start_date": date_str,
        "end_date": date_str,
        "timezone": "Asia/Jerusalem",
    }

    for attempt, backoff in enumerate(BACKOFFS, 1):
        try:
            r = requests.get(url, params=params, timeout=20)
            r.raise_for_status()
            data = r.json()

            hourly = data.get("hourly")
            if not hourly:
                return None

            times = hourly.get("time")
            rain = hourly.get("precipitation")

            if not times or not rain:
                return None

            found_any_hour = False
            for t, p in zip(times, rain):
                hour = int(t.split("T")[1][:2])
                if START_HOUR <= hour <= END_HOUR:
                    found_any_hour = True
                    if p and p > 0:
                        return True

            if found_any_hour:
                return False

            return None

        except (ReadTimeout, RequestException):
            if attempt == MAX_RETRIES:
                return None
            time.sleep(backoff)


def build_summary_for_day(date_str, bootstrap):
    parts = []
    for region, (lat, lon) in LAT_LON.items():
        try:
            status = fetch_rain_status(lat, lon, date_str, bootstrap)
            if status is True:
                icon = "🔵"
            elif status is False:
                icon = "🟡"
            else:
                icon = "⚪"
        except Exception:
            icon = "❌"

        parts.append(f"{icon}{region}")

    return " ".join(parts)


def write_event(f, date):
    date_str = date.isoformat()
    ymd = date_str.replace("-", "")

    summary = build_summary_for_day(date_str, bootstrap=True)

    f.write("BEGIN:VEVENT\n")
    f.write(f"UID:{date_str}@weather\n")
    f.write(f"DTSTAMP:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}\n")
    f.write(f"DTSTART;VALUE=DATE:{ymd}\n")
    f.write(f"DTEND;VALUE=DATE:{ymd}\n")
    f.write(f"SUMMARY:{summary}\n")
    f.write("END:VEVENT\n")


def git_commit(msg):
    subprocess.run(["git", "add", ICS_FILE, SUMMARY_FILE], check=True)
    subprocess.run(["git", "commit", "-m", msg], check=True)
    subprocess.run(["git", "push"], check=True)


# ===== MAIN =====

def main():
    bootstrap = os.getenv("BOOTSTRAP_HISTORY") == "true"
    today = datetime.now(timezone.utc).date()

    start = today - timedelta(days=BOOTSTRAP_DAYS if bootstrap else 1)
    end = today - timedelta(days=1)

    log(f"🚀 Start run | bootstrap={bootstrap}")
    log(f"📆 Range: {start} → {end}")

    with open(ICS_FILE, "w", encoding="utf-8") as f:
        f.write("BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//Weather Israel//EN\n")

        cur = start
        while cur <= end:
            write_event(f, cur)
            log(f"✅ {cur}")
            cur += timedelta(days=1)

        f.write("END:VCALENDAR\n")

    git_commit(f"Update weather up to {end}")

    log("🎉 Done")


if __name__ == "__main__":
    main()
