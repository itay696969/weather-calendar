import os
import re
import requests
import subprocess
from datetime import datetime, timedelta, timezone

# ===== CONFIG =====

LAT_LON = {
    "צ": (32.7940, 34.9896),
    "מ": (32.0853, 34.7818),
    "ד": (31.252973, 34.791462),
    "י": (31.7683, 35.2137),
}

ICS_FILE = "weather.ics"
SUMMARY_FILE = "summary.txt"
BOOTSTRAP_DAYS = 60  # ✅ כאן היה חסר!

# ===== WEATHER =====

def fetch_rain_status(lat, lon, date_str):
    try:
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "hourly": "precipitation",
                "start_date": date_str,
                "end_date": date_str,
                "timezone": "Asia/Jerusalem",
            },
            timeout=10,
        )
        r.raise_for_status()
        rain = r.json().get("hourly", {}).get("precipitation", [])
        return any(p > 0 for p in rain)
    except Exception:
        return None

def build_summary(date_str):
    parts = []
    for region, (lat, lon) in LAT_LON.items():
        status = fetch_rain_status(lat, lon, date_str)
        icon = "🔵" if status is True else "🟡" if status is False else "❌"
        parts.append(f"{icon}{region}")
    return " ".join(parts)

# ===== ICS =====

def write_ics(days_back):
    today = datetime.now(timezone.utc).date()
    existing = {}

    if os.path.exists(ICS_FILE):
        with open(ICS_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        for m in re.finditer(r"BEGIN:VEVENT.*?UID:(.*?)\n.*?END:VEVENT", content, re.S):
            existing[m.group(1)] = m.group(0)

    for i in range(1, days_back + 1):
        day = today - timedelta(days=i)
        uid = f"{day.isoformat()}@weather"
        if uid in existing:
            continue

        ymd = day.strftime("%Y%m%d")
        event = "\n".join([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
            f"DTSTART;VALUE=DATE:{ymd}",
            f"DTEND;VALUE=DATE:{ymd}",
            f"SUMMARY:{build_summary(day.isoformat())}",
            "END:VEVENT",
        ])
        existing[uid] = event

    with open(ICS_FILE, "w", encoding="utf-8") as f:
        f.write(
            "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//Weather Israel//EN\n"
            + "\n".join(existing[k] for k in sorted(existing, reverse=True))
            + "\nEND:VCALENDAR\n"
        )

# ===== GIT =====

def git_commit():
    with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
        f.write(f"Last run: {datetime.now(timezone.utc).isoformat()}")

    subprocess.run(["git", "add", ICS_FILE, SUMMARY_FILE], check=True)
    subprocess.run(["git", "commit", "-m", "Update weather calendar"], check=False)
    subprocess.run(["git", "push"], check=True)

# ===== MAIN =====

def main():
    bootstrap = os.getenv("BOOTSTRAP_HISTORY", "").lower() == "true"
    days = BOOTSTRAP_DAYS if bootstrap else 1
    write_ics(days)
    git_commit()

if __name__ == "__main__":
    main()
