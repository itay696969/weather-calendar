import requests
import os
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

# ===== HELPERS =====

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
        data = r.json()
        rain = data.get("hourly", {}).get("precipitation", [])
        return any(p and p > 0 for p in rain)
    except Exception:
        return None


def build_summary(date_str):
    parts = []
    for region, (lat, lon) in LAT_LON.items():
        status = fetch_rain_status(lat, lon, date_str)
        if status is True:
            icon = "🔵"
        elif status is False:
            icon = "🟡"
        else:
            icon = "❌"
        parts.append(f"{icon}{region}")
    return " ".join(parts)


def write_ics(start_date, days_back=90):
    events = []

    for i in range(days_back):
        date = start_date - timedelta(days=i)
        date_str = date.isoformat()
        ymd = date_str.replace("-", "")
        summary = build_summary(date_str)

        events.append(
            f"""BEGIN:VEVENT
UID:{date_str}@weather
DTSTAMP:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}
DTSTART;VALUE=DATE:{ymd}
DTEND;VALUE=DATE:{ymd}
SUMMARY:{summary}
END:VEVENT"""
        )

    with open(ICS_FILE, "w", encoding="utf-8") as f:
        f.write(
            "BEGIN:VCALENDAR\n"
            "VERSION:2.0\n"
            "PRODID:-//Weather Israel//EN\n"
            + "\n".join(events)
            + "\nEND:VCALENDAR\n"
        )


def git_commit():
    # תמיד מכריח שינוי
    with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
        f.write(f"Last run: {datetime.now(timezone.utc).isoformat()}")

    subprocess.run(["git", "add", ICS_FILE, SUMMARY_FILE], check=True)
    subprocess.run(
        ["git", "commit", "-m", f"Force update {datetime.now().isoformat()}"],
        check=False,
    )
    subprocess.run(["git", "push"], check=True)


# ===== MAIN =====

def main():
    yesterday = datetime.now(timezone.utc).date() - timedelta(days=1)
    write_ics(yesterday, days_back=90)
    git_commit()


if __name__ == "__main__":
    main()
