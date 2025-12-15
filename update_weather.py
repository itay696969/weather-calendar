import requests
import os
import time
from datetime import datetime, timedelta, timezone

LAT_LON = {
    "צ": (32.7940, 34.9896),   # צפון
    "מ": (32.0853, 34.7818),   # מרכז
    "ד": (31.252973, 34.791462),  # דרום
    "י": (31.7683, 35.2137),   # ירושלים
}

START_HOUR = 8
END_HOUR = 19
ICS_FILE = "weather.ics"
BOOTSTRAP_DAYS = 90

API_URL = "https://api.open-meteo.com/v1/forecast"

def fetch_precipitation(lat, lon, date):
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "precipitation",
        "start_date": date,
        "end_date": date,
        "timezone": "Asia/Jerusalem",
    }
    r = requests.get(API_URL, params=params, timeout=20)
    r.raise_for_status()
    return r.json()["hourly"]

def was_rainy(lat, lon, date):
    backoffs = [0.5, 1, 2, 4]

    for attempt, delay in enumerate(backoffs, start=1):
        try:
            data = fetch_precipitation(lat, lon, date)
            for t, r in zip(data["time"], data["precipitation"]):
                hour = int(t.split("T")[1][:2])
                if START_HOUR <= hour <= END_HOUR and r and r > 0:
                    return True
            return False

        except Exception as e:
            if attempt == len(backoffs):
                raise
            time.sleep(delay)

    raise RuntimeError("Unreachable")

def build_title(date):
    parts = []
    for k, (lat, lon) in LAT_LON.items():
        rainy = was_rainy(lat, lon, date)
        dot = "🔵" if rainy else "🟡"
        parts.append(f"{dot}{k}")
        time.sleep(0.2)  # האטה בין אזורים
    return " ".join(parts)

def write_event(f, date):
    title = build_title(date)
    d = date.replace("-", "")
    uid = f"{date}@weather"

    f.write("BEGIN:VEVENT\n")
    f.write(f"UID:{uid}\n")
    f.write(f"DTSTAMP:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}\n")
    f.write(f"DTSTART;VALUE=DATE:{d}\n")
    f.write(f"DTEND;VALUE=DATE:{d}\n")
    f.write(f"SUMMARY:{title}\n")
    f.write("END:VEVENT\n")

def main():
    today = datetime.now(timezone.utc).date()
    bootstrap = os.getenv("BOOTSTRAP_HISTORY") == "true"

    if bootstrap:
        start = today - timedelta(days=BOOTSTRAP_DAYS)
    else:
        start = today - timedelta(days=1)

    end = today - timedelta(days=1)

    with open(ICS_FILE, "w", encoding="utf-8") as f:
        f.write("BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//Weather Israel//EN\n")

        cur = start
        while cur <= end:
            try:
                write_event(f, cur.isoformat())
            except Exception as e:
                if not bootstrap:
                    raise
                # bootstrap: מדלגים על יום בעייתי
            cur += timedelta(days=1)

        f.write("END:VCALENDAR\n")

if __name__ == "__main__":
    main()
