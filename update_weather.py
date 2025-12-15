import requests
from datetime import datetime, timedelta, timezone

# ========= CONFIG =========
LAT_LON = {
    "צ": (32.7940, 34.9896),   # צפון – חיפה
    "מ": (32.0853, 34.7818),   # מרכז – תל אביב
    "ד": (31.252973, 34.791462),  # דרום – באר שבע
    "י": (31.7683, 35.2137),   # ירושלים
}

START_HOUR = 8
END_HOUR = 19
ICS_FILE = "weather.ics"
# ==========================

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
    data = requests.get(url, params=params, timeout=20).json()
    hours = data["hourly"]["time"]
    rain = data["hourly"]["precipitation"]

    for h, r in zip(hours, rain):
        hour = int(h.split("T")[1].split(":")[0])
        if START_HOUR <= hour <= END_HOUR and r > 0:
            return True
    return False

def build_event_title(date):
    parts = []
    for region, (lat, lon) in LAT_LON.items():
        rainy = was_rainy(lat, lon, date)
        dot = "🔵" if rainy else "🟡"
        parts.append(f"{dot}{region}")
    return " ".join(parts)

def main():
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date().isoformat()
    title = build_event_title(yesterday)

    with open(ICS_FILE, "w", encoding="utf-8") as f:
        f.write("BEGIN:VCALENDAR\n")
        f.write("VERSION:2.0\n")
        f.write("PRODID:-//Weather Dots Israel//EN\n")
        f.write("BEGIN:VEVENT\n")
        f.write(f"UID:{yesterday}@weather\n")
        f.write(f"DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}\n")
        f.write(f"DTSTART;VALUE=DATE:{yesterday.replace('-', '')}\n")
        f.write(f"DTEND;VALUE=DATE:{yesterday.replace('-', '')}\n")
        f.write(f"SUMMARY:{title}\n")
        f.write("END:VEVENT\n")
        f.write("END:VCALENDAR\n")

if __name__ == "__main__":
    main()
