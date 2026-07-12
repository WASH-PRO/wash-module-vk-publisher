**Language:** **English** · [Русский](README.ru.md)

# wash-module-vk-publisher

WASH PRO CRM module: publish entries from **Publications** to a VK community.

## Features

- Polls `GET /api/crm/info-messages`
- Publishes to VK when `publishedAt` is reached
- Category filter (`news`, `promotion`, `general`)
- Uploads image from `imageUrl` to VK (full post with photo)
- Published entries log in `data/published_vk.json`

## Settings

| Parameter | Description |
|-----------|-------------|
| `vk_access_token` | VK API token (wall, groups, photos) |
| `vk_group_id` | Community ID without minus sign |
| `poll_interval` | CRM check interval (sec) |
| `publish_categories` | Comma-separated categories |

## Install

Dashboard → Automation → Modules → **VK Publisher** → Install → Settings → Start.
