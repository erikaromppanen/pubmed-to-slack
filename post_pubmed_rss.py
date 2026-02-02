import json
import os
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


def main() -> None:
    rss_url = os.environ["RSS_URL"]
    webhook = os.environ["SLACK_WEBHOOK"]
    state_file = os.environ["STATE_FILE"]
    label = os.environ.get("CHANNEL_LABEL", "").strip()

    posted = load_state(state_file)

    feed = feedparser.parse(rss_url)
    entries = feed.entries or []

    def entry_id(entry) -> str:
        return (
            getattr(entry, "id", None)
            or getattr(entry, "guid", None)
            or getattr(entry, "link", None)
            or ""
        ).strip()

    items = []
    for entry in entries:
        eid = entry_id(entry)
        if not eid:
            continue
        title = (getattr(entry, "title", "") or "").strip()
        link = (getattr(entry, "link", "") or "").strip()
        items.append((eid, title, link))

    new_items = [
        (eid, title, link)
        for (eid, title, link) in reversed(items)
        if eid not in posted
    ]

    for eid, title, link in new_items:
        prefix = f"{label}\n" if label else ""
        text = f"{prefix}*{title}*\n{link}".strip()
        slack_post(webhook, text)
        posted.add(eid)
        time.sleep(0.5)

    save_state(state_file, posted)


if __name__ == "__main__":
    main()
