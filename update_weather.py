import requests
import os
import time
import random
import json
import subprocess
from datetime import datetime, timedelta, timezone
from requests.exceptions import ReadTimeout, RequestException

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

MAX_RETRIES = 4
BACKOFFS = [0.5, 1, 2, 4]

MIN_SLEEP = 5
MAX_SLEEP = 35
MIN_COMMITS = 50
MAX_COMMITS = 150

LOG_JSON = "commit_log.json"
LOG_SUMMARY = "summary.txt"


def log_summary(msg):
    with open(LOG_SUMMARY, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(msg)


def was_rainy(lat, lon, date, bootstrap):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "precipitation",
        "start_date": date,
        "end_date": date,
        "timezone": "Asia/Jerusalem",
    }

    for attempt, backoff in enumerate(BACKOFFS, 1):
        try:
            r = requests.get(url, params=params, timeout=20)
            r.raise_for_status()
            data = r.json()

            hours = data.get("hourly", {}).get("time")
            rain = data.get("hourly", {}).get("precipitation")

            if not hours or not rain:
                return None  # ❌ אין נתונים

            for t, p in zip(hours, rain):
                hour = int(t.split("T")[1][:2])
                if START_HOUR <= hour <= END_HOUR and p > 0:
                    return True
            return False

        except (ReadTimeout, RequestException):
            if attempt == MAX_RETRIES:
                if bootstrap:
                    return None  # ❌ מדלגים
                raise
            time.sleep(backoff)


def build_title(date, bootstrap):
    parts = []
    for k, (lat, lon) in LAT_LON.items():
        try:
            rainy = was_rainy(lat, lon, date, bootstrap)
            if rainy is None:
                dot = "❌"
            else:
                dot = "🔵" if rainy else "🟡"
        except Exception:
            dot = "❌"
        parts.append(f"{dot}{k}")
    return " ".join(parts)


def write_event(f, date, bootstrap):
    uid = f"{date}@weather"
    title = build_title(date, bootstrap)
    d = date.replace("-", "")

    f.write("BEGIN:VEVENT\n")
    f.write(f"UID:{uid}\n")
    f.write(f"DTSTAMP:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}\n")
    f.write(f"DTSTART;VALUE=DATE:{d}\n")
    f.write(f"DTEND;VALUE=DATE:{d}\n")
    f.write(f"SUMMARY:{title}\n")
    f.write("END:VEVENT\n")


def git_commit(msg):
    subprocess.run(["git", "add", ICS_FILE, LOG_JSON, LOG_SUMMARY], check=True)
    subprocess.run(["git", "commit", "-m", msg], check=True)
    subprocess.run(["git", "push"], check=True)


def main():
    bootstrap = os.getenv("BOOTSTRAP_HISTORY") == "true"
    today = datetime.now(timezone.utc).date()

    start = today - timedelta(days=BOOTSTRAP_DAYS if bootstrap else 1)
    end = today - timedelta(days=1)

    total_days = (end - start).days + 1
    max_commits = random.randint(MIN_COMMITS, MAX_COMMITS)
    days_per_commit = max(1, total_days // max_commits)

    log_summary(f"🚀 Start run | bootstrap={bootstrap}")
    log_summary(f"📆 Range: {start} → {end}")
    log_summary(f"📦 days/commit ≈ {days_per_commit}")

    commit_log = []
    cur = start
    counter = 0

    with open(ICS_FILE, "w", encoding="utf-8") as f:
        f.write("BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//Weather Israel//EN\n")

        while cur <= end:
            date_str = cur.isoformat()
            try:
                write_event(f, date_str, bootstrap)
                log_summary(f"✅ {date_str}")
            except Exception as e:
                log_summary(f"🔥 FAIL {date_str}: {e}")
                if not bootstrap:
                    raise

            counter += 1
            cur += timedelta(days=1)

            if counter % days_per_commit == 0 or cur > end:
                f.write("END:VCALENDAR\n")
                f.flush()

                msg = f"Update weather up to {date_str}"
                git_commit(msg)

                commit_log.append({
                    "date": date_str,
                    "commit": msg,
                    "timestamp": datetime.utcnow().isoformat()
                })

                sleep_s = random.randint(MIN_SLEEP, MAX_SLEEP)
                log_summary(f"⏸️ Sleep {sleep_s}s")
                time.sleep(sleep_s)

                f.write("BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//Weather Israel//EN\n")

    with open(LOG_JSON, "w", encoding="utf-8") as jf:
        json.dump(commit_log, jf, indent=2, ensure_ascii=False)

    log_summary("🎉 Done")


if __name__ == "__main__":
    main()
