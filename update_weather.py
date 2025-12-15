import os
import re
import requests
import subprocess
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
BOOTSTRAP_DAYS = 60   # ⬅️ כאן קובע ההיסטוריה

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
    existing_events = {}

    if os.path.exists(ICS_FILE):
        with open(ICS_FILE, "r", encoding="utf-8") as f:
            content = f.read()

        for match in re.finditer(
            r"BEGIN:VEVENT.*?UID:(?P<uid>.*?)\n.*?END:VEVENT",
            content,
            re.DOTALL,
        ):
            uid = match.group("uid").strip()
            existing_events[uid] = match.group(0).strip()

    added = 0

    for i in range(1, days_back + 1):
        day = today - timedelta(days=i)
        date_str = day.isoformat()
        uid = f"{date_str}@weather"

        if uid in existing_events:
            continue

        ymd = date_str.replace("-", "")
        summary = build_summary(date_str)

        event = "\n".join([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
            f"DTSTART;VALUE=DATE:{ymd}",
            f"DTEND;VALUE=DATE:{ymd}",
            f"SUMMARY:{summary}",
            "END:VEVENT",
        ])

        existing_events[uid] = event
        added += 1

    sorted_uids = sorted(existing_events.keys(), reverse=True)

    with open(ICS_FILE, "w", encoding="utf-8") as f:
        f.write(
            "BEGIN:VCALENDAR\n"
            "VERSION:2.0\n"
            "PRODID:-//Weather Israel//EN\n"
            + "\n".join(existing_events[uid] for uid in sorted_uids)
            + "\nEND:VCALENDAR\n"
        )

    return added

# ===== GIT =====

def git_commit(added):
    with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
        f.write(
            f"Last run: {datetime.now(timezone.utc).isoformat()}\n"
            f"Events added: {added}\n"
        )

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

    added = write_ics(days_back)
    git_commit(added)

if __name__ == "__main__":
    main()
