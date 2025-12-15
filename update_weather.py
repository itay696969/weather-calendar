import requests
import os
from datetime import datetime, timedelta, timezone

LAT_LON = {
    "צ": (32.7940, 34.9896),
    "מ": (32.0853, 34.7818),
    "ד": (31.252973, 34.791462),
    "י": (31.7683, 35.2137),
}

START_HOUR = 8
END_HOUR = 19
ICS_FILE = "weather.ics"
BOOTSTRAP_DAYS = 90

def was_rainy(lat, lon, date):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "precipitation",
        "start_date": date,
        "end_date": date,
        "timezone": "Asia/Jerusalem",
    }

    try:
        resp = requests.get(url, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"⚠️ Weather fetch failed for {date} ({lat},{lon}): {e}")
        return False  # לא מפיל את כל הריצה

    for t, r in zip(data["hourly"]["time"], data["hourly"]["precipitation"]):
        hour = int(t.split("T")[1][:2])
        if START_HOUR <= hour <= END_HOUR and (r or 0) > 0:
            return True

    return False


def build_title(date):
    parts = []
    for k, (lat, lon) in LAT_LON.items():
        dot = "🔵" if was_rainy(lat, lon, date) else "🟡"
        parts.append(f"{dot}{k}")
    return " ".join(parts)

def write_event(f, date):
    uid = f"{date}@weather"
    title = build_title(date)
    d = date.replace("-", "")
    f.write("BEGIN:VEVENT\n")
    f.write(f"UID:{uid}\n")
    f.write(f"DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}\n")
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
            write_event(f, cur.isoformat())
            cur += timedelta(days=1)
        f.write("END:VCALENDAR\n")

if __name__ == "__main__":
    main()
