import requests
import pathlib
import re

# Microsoft Teams Webhook-URL (bestehende Webhook nutzen)
TEAMS_WEBHOOK_URL = "hereWebhookURL"

# Liste der zu überwachenden URLs
URLS = {
    "Wasserwacht": "https://veranstaltungen.brk.de/public/FBE.php?FB=WW&SS=&ZRV=2025-02-18&ZRB=9999-99-99&ZUX=-1&ZUY=-1&ZUD=10000&TT=",
    "Motorboot": "https://veranstaltungen.brk.de/public/FBE.php?FB=WWM&SS=&ZRV=2025-02-18&ZRB=9999-99-99&ZUX=-1&ZUY=-1&ZUD=10000&TT=",
    "Naturschutz": "https://veranstaltungen.brk.de/public/FBE.php?FB=WWN&SS=&ZRV=2025-02-18&ZRB=9999-99-99&ZUX=-1&ZUY=-1&ZUD=10000&TT=",
    "Rettungschwimmen": "https://veranstaltungen.brk.de/public/FBE.php?FB=WWRS&SS=&ZRV=2025-02-18&ZRB=9999-99-99&ZUX=-1&ZUY=-1&ZUD=10000&TT=",
    "Schwimmen": "https://veranstaltungen.brk.de/public/FBE.php?FB=WWS&SS=&ZRV=2025-02-18&ZRB=9999-99-99&ZUX=-1&ZUY=-1&ZUD=10000&TT=",
    "Tauchen": "https://veranstaltungen.brk.de/public/FBE.php?FB=WWT&SS=&ZRV=2025-02-18&ZRB=9999-99-99&ZUX=-1&ZUY=-1&ZUD=10000&TT=",
    "Wasserrettung": "https://veranstaltungen.brk.de/public/FBE.php?FB=WWWR&SS=&ZRV=2025-02-18&ZRB=9999-99-99&ZUX=-1&ZUY=-1&ZUD=10000&TT=",
    "Führung": "https://veranstaltungen.brk.de/public/FBE.php?FB=WWF%DC&SS=&ZRV=2025-02-19&ZRB=9999-99-99&ZUX=-1&ZUY=-1&ZUD=10000&TT="
}

# Speicherort für alte Versionen
DATA_DIR = pathlib.Path("brk_data")
DATA_DIR.mkdir(exist_ok=True)

def save_page_source(category, url):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    response.encoding = "iso-8859-1"
    
    output_file = DATA_DIR / f"{category}.html"
    old_output_file = DATA_DIR / f"{category}_old.html"
    
    if output_file.exists():
        if old_output_file.exists():
            old_output_file.unlink()
        output_file.rename(old_output_file)
    
    output_file.write_text(response.text, encoding="iso-8859-1")

def extract_courses(content):
    matches = re.findall(r"<label .*?>(.*?)</label><label .*?>(\d{2}\.\d{2}\.\d{4} - \d{2}\.\d{2}\.\d{4})</label>.*?location\.href='(LGE\.php\?LG=\d+)'", content, re.DOTALL)
    courses = [{
        "title": title.strip(),
        "date": date.strip(),
        "link": f"https://veranstaltungen.brk.de/public/{link.strip()}"
    } for title, date, link in matches]
    return courses

def send_teams_notification(category, new_courses):
    if not new_courses:
        print(f"ℹ️ Keine neuen Kurse für {category}.")
        return
    
    message = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "version": "1.4",
                    "type": "AdaptiveCard",
                    "body": [
                        {"type": "TextBlock", "text": f"🚀 Neue {category}-Lehrgänge gefunden:", "weight": "Bolder", "size": "Medium"}
                    ] + [
                        {"type": "TextBlock", "text": f"**{course['title']}**\n📅 {course['date']}", "wrap": True}
                        for course in new_courses
                    ],
                    "actions": [
                        {"type": "Action.OpenUrl", "title": course['title'], "url": course['link']}
                        for course in new_courses
                    ]
                }
            }
        ]
    }
    
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(TEAMS_WEBHOOK_URL, json=message, headers=headers, timeout=10)
        response.raise_for_status()
        print(f"✅ Microsoft Teams Benachrichtigung für {category} gesendet.")
    except requests.exceptions.RequestException as e:
        print(f"❌ Fehler beim Senden der Teams Benachrichtigung für {category}:", e)

def check_for_new_entries():
    for category, url in URLS.items():
        save_page_source(category, url)
        
        output_file = DATA_DIR / f"{category}.html"
        old_output_file = DATA_DIR / f"{category}_old.html"
        
        if not old_output_file.exists():
            print(f"ℹ️ Keine alte Version für {category}. Erste Speicherung durchgeführt.")
            continue
        
        new_content = output_file.read_text(encoding="iso-8859-1")
        old_content = old_output_file.read_text(encoding="iso-8859-1")
        
        new_courses = extract_courses(new_content)
        old_courses = extract_courses(old_content)
        old_links = {course['link'] for course in old_courses}
        new_entries = [course for course in new_courses if course['link'] not in old_links]
        
        if new_entries:
            print(f"🚀 Neue Lehrgänge für {category} gefunden:")
            for course in new_entries:
                print(f"{course['title']} - {course['date']} - {course['link']}")
            send_teams_notification(category, new_entries)
        else:
            print(f"✅ Keine neuen Einträge für {category} gefunden.")

check_for_new_entries()
