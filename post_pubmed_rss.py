import html
import json
import os
import re
import time

import feedparser
import requests

def load_state(path: str) -> set[str]:
    if not os.path.exists(path):
        return set()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return set(data.get("posted", []))

def save_state(path: str, posted: set[str]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"posted": sorted(posted)}, f, ensure_ascii=False, indent=2)

def slack_post(webhook: str, text: str) -> None:
    resp = requests.post(webhook, json={"text": text}, timeout=30)
    resp.raise_for_status()

def extract_abstract(entry) -> str:
    summary = (getattr(entry, "summary", "") or "").strip()
    if summary:
        return summary
    return (getattr(entry, "description", "") or "").strip()

def sanitize_text(text: str) -> str:
    if not text:
        return ""
    cleaned = html.unescape(text)
    cleaned = re.sub(r"(?i)<\s*br\s*/?\s*>", "\n", cleaned)
    cleaned = re.sub(r"(?i)</\s*p\s*>", "\n", cleaned)
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    return cleaned.strip()

def slack_escape_label(text: str) -> str:
    if not text:
        return ""
    # Slack link labels cannot contain these characters unescaped.
    return text.replace("|", "¦").replace(">", "›").replace("<", "‹")

def main() -> None:
    rss_url = os.environ["RSS_URL"]
    webhook = os.environ["SLACK_WEBHOOK"]
    state_file = os.environ["STATE_FILE"]
    label = os.environ.get("CHANNEL_LABEL", "").strip()
    abstract_chars = int(os.environ.get("ABSTRACT_CHARS", "400"))
    rss_timeout = int(os.environ.get("RSS_TIMEOUT", "30"))

    # If state is empty, treat this as "first run" initialization:
    posted = load_state(state_file)

    response = requests.get(rss_url, timeout=rss_timeout)
    response.raise_for_status()
    feed = feedparser.parse(response.content)
    entries = feed.entries or []

    def entry_id(e) -> str:
        return (getattr(e, "id", None) or getattr(e, "guid", None) or getattr(e, "link", None) or "").strip()

    items = []
    for e in entries:
        eid = entry_id(e)
        if not eid:
            continue
        title = slack_escape_label(sanitize_text((getattr(e, "title", "") or "").strip()))
        link = (getattr(e, "link", "") or "").strip()
        abstract = sanitize_text(extract_abstract(e))
        items.append((eid, title, link, abstract))

    # FIRST RUN BEHAVIOR:
    # If nothing has been posted yet, we "prime" the state with whatever is already in the feed,
    # and we do NOT post anything. This ensures only future papers get posted.
    if len(posted) == 0:
        for eid, _, _, _ in items:
            posted.add(eid)
        save_state(state_file, posted)
        print(f"Initialized state with {len(items)} existing RSS items. No Slack posts sent.")
        return

    # Normal behavior: post only items not seen before (oldest -> newest)
    new_items = [
        (eid, title, link, abstract)
        for (eid, title, link, abstract) in reversed(items)
        if eid not in posted
    ]

    for eid, title, link, abstract in new_items:
        prefix = f"{label}\n" if label else ""
        title_line = f"<{link}|{title}>" if link and title else title or link
        if title_line:
            title_line = f"*{title_line}*"
        abstract_text = (abstract or "").strip()
        if abstract_chars > 0 and len(abstract_text) > abstract_chars:
            abstract_text = abstract_text[:abstract_chars].rstrip() + "…"
        if abstract_text:
            text = f"{prefix}{title_line}\n{abstract_text}".strip()
        else:
            text = f"{prefix}{title_line}".strip()
        slack_post(webhook, text)
        posted.add(eid)
        save_state(state_file, posted)
        time.sleep(0.5)

    save_state(state_file, posted)
    print(f"Posted {len(new_items)} new items.")

if __name__ == "__main__":
    main()
