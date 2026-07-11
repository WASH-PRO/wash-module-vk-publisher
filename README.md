# wash-module-vk-publisher

Модуль WASH PRO CRM: публикация записей из раздела **Публикации** в сообщество ВКонтакте.

## Возможности

- Опрос `GET /api/crm/info-messages`
- Публикация в VK при наступлении `publishedAt`
- Фильтр по категориям (`news`, `promotion`, `general`)
- Журнал опубликованных записей в `data/published_vk.json`

## Настройки

| Параметр | Описание |
|----------|----------|
| `vk_access_token` | Токен VK API (wall, groups) |
| `vk_group_id` | ID сообщества без минуса |
| `poll_interval` | Интервал проверки CRM (сек) |
| `publish_categories` | Категории через запятую |

## Установка

Dashboard → Автоматизация → Модули → **VK публикатор** → Установить → Настройки → Запустить.
