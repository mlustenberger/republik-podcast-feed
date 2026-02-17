import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import format_datetime

SEEN_FILE = "seen.json"

def rfc2822_now() -> str:
    return format_datetime(datetime.now(timezone.utc))

def add(el, tag, value):
    child = ET.SubElement(el, tag)
    child.text = value if value is not None else ""
    return child

# Load source JSON
with open("reeder-feed.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Load / init seen map (episodeKey -> pubDate RFC2822)
try:
    with open(SEEN_FILE, "r", encoding="utf-8") as f:
        seen = json.load(f)
except FileNotFoundError:
    seen = {}

build_now = rfc2822_now()

rss = ET.Element("rss", {"version": "2.0"})
rss.set("xmlns:itunes", "http://www.itunes.com/dtds/podcast-1.0.dtd")

channel = ET.SubElement(rss, "channel")
add(channel, "title", data.get("title", "Republik Podcast"))
add(channel, "link", data.get("home_page_url", "https://reederapp.net/fv-EicT8SqiraESmO1YElA"))
add(channel, "description", "Custom Feed (generiert aus Reeder JSON)")
add(channel, "language", "de-CH")
add(channel, "lastBuildDate", build_now)

items = data.get("items", []) or []
for it in items[:50]:
    item = ET.SubElement(channel, "item")

    title = it.get("title", "")
    url = it.get("url", "")
    add(item, "title", title)
    add(item, "link", url)

    key = it.get("id") or url or title
    guid = ET.SubElement(item, "guid", {"isPermaLink": "false"})
    guid.text = key

    # pubDate: beim ersten Auftauchen "jetzt", danach stabil aus seen.json
    if key not in seen:
        seen[key] = build_now
    add(item, "pubDate", seen[key])

    # Audio
    reeder = it.get("_reeder", {}) or {}
    media = reeder.get("media", []) or []
    if media:
        m0 = media[0] or {}
        media_url = m0.get("url")
        if media_url:
            enc = ET.SubElement(item, "enclosure")
            enc.set("url", media_url)
            enc.set("type", m0.get("mime_type", "audio/mpeg"))
            size = m0.get("size_in_bytes")
            enc.set("length", str(size if isinstance(size, int) else 0))

        dur = m0.get("duration")
        if isinstance(dur, (int, float)) and dur > 0:
            secs = int(dur)
            h = secs // 3600
            m = (secs % 3600) // 60
            s = secs % 60
            add(item, "itunes:duration", f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}")

    # Optional text
    content = it.get("content_text") or it.get("summary") or ""
    if content:
        content = re.sub(r"\s+", " ", content).strip()[:2000]
        add(item, "description", content)

# Write RSS
xml_bytes = ET.tostring(rss, encoding="utf-8", xml_declaration=True)
with open("podcast.rss", "wb") as f:
    f.write(xml_bytes)

# Persist seen map
with open(SEEN_FILE, "w", encoding="utf-8") as f:
    json.dump(seen, f, ensure_ascii=False, indent=2)
