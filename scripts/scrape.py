#!/usr/bin/env python3
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
CAMPAIGNS_FILE = ROOT / "campaigns.json"
DATA_DIR = ROOT / "docs" / "data"
LATEST_FILE = DATA_DIR / "latest.json"
HISTORY_FILE = DATA_DIR / "history.json"

MONEY_PATTERN = re.compile(r"\$\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?|[0-9]+(?:\.[0-9]{2})?)")
NUMBER_PATTERN = re.compile(r"([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.([0-9]{1,2}))?")


@dataclass
class TeamResult:
    id: str
    name: str
    url: str
    raised_cents: int
    raised_display: str


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")


def cents_to_display(cents: int) -> str:
    return f"${cents / 100:,.2f}"


def parse_money_to_cents(text: str) -> Optional[int]:
    match = MONEY_PATTERN.search(text)
    if not match:
        return None
    amount = match.group(1).replace(",", "")
    return int(round(float(amount) * 100))


def parse_amount_to_cents(text: str) -> Optional[int]:
    match = NUMBER_PATTERN.search(text)
    if not match:
        return None

    dollars = int(match.group(1).replace(",", ""))
    cents_part = match.group(2)
    if cents_part is None:
        cents = 0
    elif len(cents_part) == 1:
        cents = int(cents_part) * 10
    else:
        cents = int(cents_part[:2])
    return dollars * 100 + cents


def extract_support_area_json(html: str) -> Optional[dict[str, Any]]:
    marker = "var support_area = new app.Campaign("
    start = html.find(marker)
    if start == -1:
        return None

    i = start + len(marker)
    while i < len(html) and html[i].isspace():
        i += 1
    if i >= len(html) or html[i] != "{":
        return None

    depth = 0
    in_string = False
    escape = False
    obj_start = i
    for j in range(i, len(html)):
        ch = html[j]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                raw = html[obj_start : j + 1]
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    return None
    return None


def extract_stats_api_url(html: str) -> Optional[str]:
    match = re.search(r"ggStatsApiUrl:\s*'([^']+)'", html)
    if not match:
        return None
    return match.group(1)


def extract_raised_cents(html: str) -> Optional[int]:
    soup = BeautifulSoup(html, "html.parser")

    # Prefer the campaign stats panel ("Raised") over the global site header stats.
    for stat in soup.select("#profile-stats .profile-stat"):
        label_node = stat.select_one("span")
        value_node = stat.select_one(".number")
        if not label_node or not value_node:
            continue
        if label_node.get_text(" ", strip=True).lower() != "raised":
            continue
        value_text = value_node.get_text(" ", strip=True)
        cents = parse_money_to_cents(value_text)
        if cents is None:
            cents = parse_amount_to_cents(value_text)
        if cents is not None:
            return cents

    support_area = extract_support_area_json(html)
    if isinstance(support_area, dict):
        maybe_cents = support_area.get("total_amount_raised")
        if isinstance(maybe_cents, (int, float)):
            return int(maybe_cents)

    match = re.search(r'"total_amount_raised"\s*:\s*([0-9]+)', html)
    if match:
        return int(match.group(1))

    text_nodes = soup.find_all(string=True)
    for node in text_nodes:
        t = " ".join(str(node).split())
        lower = t.lower()
        if "raised" in lower and "$" in t:
            cents = parse_money_to_cents(t)
            if cents is not None:
                return cents

    full_text = soup.get_text(" ", strip=True)
    around_raised = re.finditer(r".{0,40}raised.{0,40}", full_text, flags=re.IGNORECASE)
    for snippet in around_raised:
        cents = parse_money_to_cents(snippet.group(0))
        if cents is not None:
            return cents

    return None


def campaign_id_from_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    parts = path.split("/")
    if len(parts) >= 2 and parts[0] == "campaigns" and parts[1]:
        return parts[1]
    raise ValueError(f"Could not derive campaign id from URL: {url}")


def fetch_team(team: dict[str, Any], timeout_sec: int = 20) -> TeamResult:
    import requests

    team_id = campaign_id_from_url(team["url"])
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; giving-day-dashboard/1.0)",
        "Accept": "text/html,application/xhtml+xml",
    }
    response = requests.get(
        team["url"],
        timeout=timeout_sec,
        headers=headers,
    )
    response.raise_for_status()

    support_area = extract_support_area_json(response.text)
    stats_api_url = extract_stats_api_url(response.text)
    if (
        isinstance(support_area, dict)
        and isinstance(support_area.get("id"), int)
        and isinstance(stats_api_url, str)
        and stats_api_url
    ):
        stats_url = f"{stats_api_url.rstrip('/')}/v1/campaigns/{support_area['id']}/stats"
        stats_resp = requests.get(
            stats_url,
            timeout=timeout_sec,
            params={"with": "goal,percent_raised"},
            headers={"User-Agent": headers["User-Agent"], "Accept": "application/json"},
        )
        stats_resp.raise_for_status()
        stats_payload = stats_resp.json()
        total_amount_raised = stats_payload.get("total_amount_raised")
        if isinstance(total_amount_raised, (int, float)):
            cents = int(total_amount_raised)
            return TeamResult(
                id=team_id,
                name=team["name"],
                url=team["url"],
                raised_cents=cents,
                raised_display=cents_to_display(cents),
            )

    cents = extract_raised_cents(response.text)
    if cents is None:
        raise ValueError(f"Could not find raised amount for {team_id} at {team['url']}")

    return TeamResult(
        id=team_id,
        name=team["name"],
        url=team["url"],
        raised_cents=cents,
        raised_display=cents_to_display(cents),
    )


def update_history(now_iso: str, results: list[TeamResult]) -> None:
    history = load_json(HISTORY_FILE, {"updated_at": None, "teams": []})
    history_map = {t["id"]: t for t in history.get("teams", [])}

    next_teams = []
    for team in results:
        entry = history_map.get(
            team.id,
            {
                "id": team.id,
                "name": team.name,
                "url": team.url,
                "points": [],
            },
        )
        points = entry.get("points", [])
        points.append(
            {
                "ts": now_iso,
                "raised_cents": team.raised_cents,
                "raised_display": team.raised_display,
            }
        )
        entry.update({"id": team.id, "name": team.name, "url": team.url, "points": points})
        next_teams.append(entry)

    history_payload = {"updated_at": now_iso, "teams": next_teams}
    save_json(HISTORY_FILE, history_payload)


def update_latest(now_iso: str, results: list[TeamResult]) -> None:
    payload = {
        "updated_at": now_iso,
        "teams": [
            {
                "id": t.id,
                "name": t.name,
                "url": t.url,
                "raised_cents": t.raised_cents,
                "raised_display": t.raised_display,
            }
            for t in results
        ],
    }
    save_json(LATEST_FILE, payload)


def main() -> None:
    campaigns = load_json(CAMPAIGNS_FILE, [])
    if not campaigns:
        raise SystemExit("campaigns.json is empty")

    now_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    results = []
    for campaign in campaigns:
        try:
            results.append(fetch_team(campaign))
        except Exception as exc:
            print(f"Warning: {exc}", file=sys.stderr)

    if not results:
        raise SystemExit("Failed to scrape all campaigns")

    update_latest(now_iso, results)
    update_history(now_iso, results)

    print(f"Updated {len(results)} teams at {now_iso}")


if __name__ == "__main__":
    main()
