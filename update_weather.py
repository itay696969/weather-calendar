import requests
import subprocess
import os
import re
from datetime import datetime, timedelta, timezone

# ===== CONFIG =====

LAT_LON = {
    "צ": (32.7940, 34.9896),      # צפון
    "מ": (32.0853, 34.7818),      # מרכז
    "ד": (31.252973, 34.791462), # דרום
    "י": (31.7683, 35.2137),      # ירושלים
}

ICS_FILE = "weather.ics"
SUMMARY_FILE = "summary.txt"

BOOTSTRAP_DAYS = 90   # 3 חודשים אחורה

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

def write_ics(days_back: int):
    today = datetime.now(timezone.utc).date()
    events = {}

    if os.path.exists(ICS_FILE):
        with open(ICS_FILE, "r", encoding="utf-8") as f:
            content = f.read()

        for m in re.finditer(
            r"BEGIN:VEVENT.*?UID:(?P<uid>.*?)\n.*?END:VEVENT",
            content,
            re.DOTALL,
        ):
            events[m.group("uid").strip()] = m.group(0).strip()

    for i in range(1, days_back + 1):
        day = today - timedelta(days=i)
        uid = f"{day}@weather"

        if uid in events:
            continue

        ymd = day.strftime("%Y%m%d")
        summary = build_summary(day.isoformat())

        events[uid] = "\n".join([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
            f"DTSTART;VALUE=DATE:{ymd}",
            f"DTEND;VALUE=DATE:{ymd}",
            f"SUMMARY:{summary}",
            "END:VEVENT",
        ])

    with open(ICS_FILE, "w", encoding="utf-8") as f:
        f.write(
            "BEGIN:VCALENDAR\n"
            "VERSION:2.0\n"
            "PRODID:-//Weather Israel//EN\n"
            + "\n".join(events[k] for k in sorted(events, reverse=True))
            + "\nEND:VCALENDAR\n"
        )

# ===== GIT =====

def git_commit():
    with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
        f.write(f"Last run: {datetime.now(timezone.utc).isoformat()}")

    subprocess.run(["git", "add", ICS_FILE, SUMMARY_FILE], check=True)
    subprocess.run(
        ["git", "commit", "-m", f"Weather update {datetime.now().isoformat()}"],
        check=False,
    )
    subprocess.run(["git", "push"], check=True)

# ===== MAIN =====

def main():
    bootstrap = (os.getenv("BOOTSTRAP_HISTORY") or "").lower() == "true"
    days_back = BOOTSTRAP_DAYS if bootstrap else 1

    write_ics(days_back)
    git_commit()

if __name__ == "__main__":
    main()
