import os, json, time
import requests
import feedparser

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

    # If state is empty, treat this as "first run" initialization:
    posted = load_state(state_file)

    feed = feedparser.parse(rss_url)
    entries = feed.entries or []

    def entry_id(e) -> str:
        return (getattr(e, "id", None) or getattr(e, "guid", None) or getattr(e, "link", None) or "").strip()

    items = []
    for e in entries:
        eid = entry_id(e)
        if not eid:
            continue
        title = (getattr(e, "title", "") or "").strip()
        link = (getattr(e, "link", "") or "").strip()
        items.append((eid, title, link))

    # FIRST RUN BEHAVIOR:
    # If nothing has been posted yet, we "prime" the state with whatever is already in the feed,
    # and we do NOT post anything. This ensures only future papers get posted.
    if len(posted) == 0:
        for eid, _, _ in items:
            posted.add(eid)
        save_state(state_file, posted)
        print(f"Initialized state with {len(items)} existing RSS items. No Slack posts sent.")
        return

    # Normal behavior: post only items not seen before (oldest -> newest)
    new_items = [(eid, title, link) for (eid, title, link) in reversed(items) if eid not in posted]

    for eid, title, link in new_items:
        prefix = f"{label}\n" if label else ""
        text = f"{prefix}*{title}*\n{link}".strip()
        slack_post(webhook, text)
        posted.add(eid)
        time.sleep(0.5)

    save_state(state_file, posted)
    print(f"Posted {len(new_items)} new items.")

if __name__ == "__main__":
    main()
