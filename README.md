# pubmed-to-slack

Free PubMed RSS → Slack pipeline using GitHub Actions. Posts one paper per message, deduplicates via a small JSON state file, and supports multiple feeds.

## How it works

- `post_pubmed_rss.py` fetches an RSS feed, finds new items, and posts each to Slack.
- `state/posted_*.json` tracks already-posted item IDs to prevent duplicates.
- GitHub Actions runs on a schedule and commits updated state back to the repo.

## Slack message format

- Title is a clickable link and **bolded**.
- Abstract preview included when available.
- Configure abstract preview length with `ABSTRACT_CHARS` (default `400`, set to `0` to disable).

## Setup

1) Create Slack Incoming Webhooks (one per channel/feed).
2) Create a GitHub repo and add these secrets:

   - `PUBMED_RSS_CCRCC`
   - `SLACK_WEBHOOK_CCRCC`
   - `PUBMED_RSS_PCA`
   - `SLACK_WEBHOOK_PCA`

3) Initialize state files (already present in this repo):

   - `state/posted_ccrcc.json`
   - `state/posted_pca.json`

4) Push to GitHub and run workflows once:

   - `.github/workflows/ccrcc.yml`
   - `.github/workflows/pca.yml`

## Environment variables

Each workflow sets:

- `RSS_URL` – PubMed RSS URL
- `SLACK_WEBHOOK` – Slack Incoming Webhook URL
- `STATE_FILE` – JSON file path for dedupe state
- `ABSTRACT_CHARS` – Optional; default `400`

## Notes

- Cron schedules run in UTC and may be delayed slightly by GitHub.
- First run initializes the state file without posting existing items.
