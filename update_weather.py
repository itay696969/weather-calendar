from datetime import date, timedelta
import uuid

ICS_PATH = "weather.ics"

def load_ics():
    try:
        with open(ICS_PATH, "r", encoding="utf-8") as f:
            return f.read().splitlines()
    except FileNotFoundError:
        return [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Weather Dots//IL//HE"
        ]

def save_ics(lines):
    if lines[-1] != "END:VCALENDAR":
        lines.append("END:VCALENDAR")
    with open(ICS_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def rain_detected(yesterday):
    # כרגע החזרה קבועה — נחליף בהמשך ל־API
    return False

def update_yesterday():
    yesterday = date.today() - timedelta(days=1)
    symbol = "🔵" if rain_detected(yesterday) else "🟡"

    lines = load_ics()

    # הסרת אירוע קיים של אתמול
    filtered = []
    skip = False
    buffer = []

    for line in lines:
        if line == "BEGIN:VEVENT":
            buffer = [line]
            skip = False
        elif line.startswith("DTSTART") and yesterday.strftime("%Y%m%d") in line:
            skip = True
            buffer = []
        elif line == "END:VEVENT":
            if not skip:
                buffer.append(line)
                filtered.extend(buffer)
            skip = False
            buffer = []
        else:
            buffer.append(line)

    uid = str(uuid.uuid4())

    filtered.extend([
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTART;VALUE=DATE:{yesterday.strftime('%Y%m%d')}",
        f"DTEND;VALUE=DATE:{(yesterday + timedelta(days=1)).strftime('%Y%m%d')}",
        f"SUMMARY:{symbol}",
        "END:VEVENT"
    ])

    save_ics(filtered)

if __name__ == "__main__":
    update_yesterday()
