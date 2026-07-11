"""WASH module: VK publisher — CRM Publications → VK wall."""

from __future__ import annotations

import html
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

API_BASE = os.environ.get("API_BASE_URL", "http://dynamic-api:3001").rstrip("/")
DATA_DIR = os.environ.get("MODULE_DATA_DIR", "/data")
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "60"))
VK_ACCESS_TOKEN = os.environ.get("VK_ACCESS_TOKEN", "").strip()
VK_GROUP_ID = os.environ.get("VK_GROUP_ID", "").strip()
PUBLISH_CATEGORIES = os.environ.get(
    "PUBLISH_CATEGORIES", "news,promotion,general"
).strip().lower()

VK_API_VERSION = "5.199"
PUBLISHED_MAP_FILE = "published_vk.json"
SNAPSHOT_FILE = "last_snapshot.json"


def load_json(path: str, default: dict | list) -> dict | list:
    if not os.path.exists(path):
        return default
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def save_json(path: str, data: dict | list) -> None:
    os.makedirs(os.path.dirname(path) or DATA_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def fetch_info_messages() -> list[dict]:
    url = f"{API_BASE}/api/crm/info-messages?limit=500"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"] if isinstance(payload["data"], list) else []
    if isinstance(payload, list):
        return payload
    return []


def parse_dt(value: str | None) -> datetime | None:
    if not value or not str(value).strip():
        return None
    raw = str(value).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def strip_html(text: str) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    cleaned = re.sub(r"</p>", "\n\n", cleaned, flags=re.I)
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    return html.unescape(cleaned).strip()


def allowed_category(category: str | None) -> bool:
    if not PUBLISH_CATEGORIES or PUBLISH_CATEGORIES == "all":
        return True
    allowed = {c.strip().lower() for c in PUBLISH_CATEGORIES.split(",") if c.strip()}
    return (category or "general").strip().lower() in allowed


def should_publish(message: dict, now: datetime) -> bool:
    status = str(message.get("status") or "").strip().lower()
    if status not in ("scheduled", "published"):
        return False

    published_at = parse_dt(message.get("publishedAt"))
    if not published_at or published_at > now:
        return False

    expires_at = parse_dt(message.get("expiresAt"))
    if expires_at and expires_at <= now:
        return False

    if not allowed_category(message.get("category")):
        return False

    return True


def build_vk_message(message: dict) -> str:
    title = str(message.get("title") or "").strip()
    body = strip_html(str(message.get("body") or ""))
    parts = []
    if title:
        parts.append(title)
    if body:
        parts.append(body)
    image_url = str(message.get("imageUrl") or "").strip()
    if image_url:
        parts.append(image_url)
    text = "\n\n".join(parts).strip()
    return text[:4096]


def vk_wall_post(message_text: str) -> dict:
    if not VK_ACCESS_TOKEN:
        raise ValueError("VK_ACCESS_TOKEN не задан")
    if not VK_GROUP_ID:
        raise ValueError("VK_GROUP_ID не задан")

    group_id = VK_GROUP_ID.lstrip("-")
    params = {
        "access_token": VK_ACCESS_TOKEN,
        "v": VK_API_VERSION,
        "owner_id": f"-{group_id}",
        "from_group": "1",
        "message": message_text,
    }
    url = "https://api.vk.com/method/wall.post?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, method="POST")
    with urllib.request.urlopen(req, timeout=45) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    if "error" in payload:
        err = payload["error"]
        code = err.get("error_code", "?")
        msg = err.get("error_msg", str(err))
        raise RuntimeError(f"VK API error {code}: {msg}")

    return payload.get("response", {})


def message_id(message: dict) -> str:
    for key in ("id", "_id"):
        if message.get(key):
            return str(message[key])
    return str(message.get("title", "")) + str(message.get("publishedAt", ""))


def run_cycle() -> dict:
    now = datetime.now(timezone.utc)
    published_map_path = os.path.join(DATA_DIR, PUBLISHED_MAP_FILE)
    published_map: dict[str, dict] = load_json(published_map_path, {})  # type: ignore[assignment]

    messages = fetch_info_messages()
    pending = [m for m in messages if should_publish(m, now) and message_id(m) not in published_map]

    published_this_cycle: list[dict] = []
    errors: list[dict] = []

    for msg in pending:
        mid = message_id(msg)
        try:
            text = build_vk_message(msg)
            if not text:
                errors.append({"id": mid, "error": "empty message"})
                continue
            response = vk_wall_post(text)
            post_id = response.get("post_id")
            published_map[mid] = {
                "crmId": mid,
                "vkPostId": post_id,
                "title": msg.get("title"),
                "publishedAt": now.isoformat(),
                "crmPublishedAt": msg.get("publishedAt"),
            }
            published_this_cycle.append(published_map[mid])
            print(f"[vk-publisher] posted crm={mid} vk_post={post_id}")
        except Exception as err:  # noqa: BLE001
            err_text = str(err)
            errors.append({"id": mid, "error": err_text, "title": msg.get("title")})
            print(f"[vk-publisher] failed crm={mid}: {err_text}")

    save_json(published_map_path, published_map)

    snapshot = {
        "recordedAt": now.isoformat(),
        "groupId": VK_GROUP_ID,
        "messagesTotal": len(messages),
        "pendingCount": len(pending),
        "publishedTotal": len(published_map),
        "publishedThisCycle": len(published_this_cycle),
        "lastPublished": published_this_cycle[-1] if published_this_cycle else None,
        "recentErrors": errors[-5:],
        "configured": bool(VK_ACCESS_TOKEN and VK_GROUP_ID),
    }
    save_json(os.path.join(DATA_DIR, SNAPSHOT_FILE), snapshot)
    return snapshot


def main() -> None:
    while True:
        try:
            snap = run_cycle()
            print(
                f"[vk-publisher] total={snap['publishedTotal']} "
                f"pending={snap['pendingCount']} this={snap['publishedThisCycle']}"
            )
        except urllib.error.URLError as err:
            print(f"[vk-publisher] CRM API error: {err}")
        except Exception as err:  # noqa: BLE001
            print(f"[vk-publisher] error: {err}")
        time.sleep(max(30, POLL_INTERVAL))


if __name__ == "__main__":
    main()
