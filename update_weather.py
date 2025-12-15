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
MAX_RETRIES = 3
REQUEST_TIMEOUT = 15


def was_rainy(lat, lon, date):
    """Return True if there was rain during daytime hours."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "precipitation",
        "start_date": date,
        "end_date": date,
        "timezone": "Asia/Jerusalem",
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            data = r.json()

            times = data.get("hourly", {}).get("time", [])
            precs = data.get("hourly", {}).get("precipitation", [])

            for t, p in zip(times, precs):
                if p is None:
                    continue
                hour = int(t.split("T")[1][:2])
                if START_HOUR <= hour <= END_HOUR and p > 0:
                    return True

            return False

        except Exception as e:
            if attempt == MAX_RETRIES:
                print(f"⚠️ Weather API failed for {date} ({lat},{lon}): {e}")
                return False
            time.sleep(2 * attempt)


def build_title(date):
    parts = []
    for k, (lat, lon) in LAT_LON.items():
        rainy = was_rainy(lat, lon, date)
        dot = "🔵" if rainy else "🟡"
        parts.append(f"{dot}{k}")
    return " ".join(parts)


def write_event(f, date):
    uid = f"{date}@weather"
    title = build_title(date)
    d = date.replace("-", "")

    f.write("BEGIN:VEVENT\n")
    f.write(f"UID:{uid}\n")
    f.write(
        f"DTSTAMP:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}\n"
    )
    f.write(f"DTSTART;VALUE=DATE:{d}\n")
    f.write(f"DTEND;VALUE=DATE:{d}\n")
    f.write(f"SUMMARY:{title}\n")
    f.write("END:VEVENT\n")


def main():
    today = datetime.now(timezone.utc).date()
    bootstrap = os.getenv("BOOTSTRAP_HISTORY") == "true"

    if bootstrap:
        start = today - timedelta(days=BOOTSTRAP_DAYS)
        print(f"🔁 Bootstrapping {BOOTSTRAP_DAYS} days")
    else:
        start = today - timedelta(days=1)

    end = today - timedelta(days=1)

    with open(ICS_FILE, "w", encoding="utf-8") as f:
        f.write("BEGIN:VCALENDAR\n")
        f.write("VERSION:2.0\n")
        f.write("PRODID:-//Weather Israel//EN\n")

        cur = start
        while cur <= end:
            print(f"📅 Processing {cur}")
            write_event(f, cur.isoformat())
            cur += timedelta(days=1)

        f.write("END:VCALENDAR\n")


if __name__ == "__main__":
    main()
