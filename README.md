# proxies

`proxy_pipeline` это async-пакет для парсеров:

- updater получает прокси из API провайдеров и обновляет БД
- парсеры читают готовые прокси из БД
- все хранение и выборка идут через SQLAlchemy

Поддерживаемые провайдеры:

- `proxyline`
- `proxy6`
- `mobileproxyspace`

## Установка

Минимально нужны:

- `aiohttp`
- `SQLAlchemy>=2`
- async-драйвер БД (`asyncpg` для PostgreSQL, `aiosqlite` для SQLite)
- `pytest` и `pytest-asyncio` для тестов

## Конфигурация

Конфигурация берется из:

1. переменных окружения
2. `proxies_config.py`
3. дефолтов

Ключи:

- `DATABASE_URL`
- `PROXYLINE_URL`
- `PROXYLINE_PARAMS` (JSON)
- `PROXY6_API_KEY`
- `PROXY6_STATE` (по умолчанию `active`)
- `MOBILEPROXYSPACE_API_TOKEN`
- `MOBILEPROXYSPACE_BASE_URL` (по умолчанию `https://mobileproxy.space/api.html`)
- `MOBILEPROXYSPACE_PROXY_IDS` (через запятую)

Пример `proxies_config.py`:

```python
DATABASE_URL = "postgresql+asyncpg://user:password@localhost/trade"

PROXYLINE = {
    "proxies_url": "https://panel.proxyline.net/api/proxies/",
    "proxies_params": {
        "orders": [123456],
        "type": "shared",
        "status": "active",
    },
}

PROXY6 = {
    "api_key": "YOUR_PROXY6_KEY",
    "state": "active",
}

MOBILEPROXYSPACE = {
    "api_token": "YOUR_MOBILEPROXYSPACE_TOKEN",
    "base_url": "https://mobileproxy.space/api.html",
    "proxy_ids": ["453401"],
    "command": "get_my_proxy",
}
```

## Бизнес-режим

Рекомендуемая модель:

- один отдельный updater-процесс ходит в сеть и обновляет БД
- парсеры только читают прокси из БД (`get_random_*`)

Это снижает нагрузку на API провайдеров и исключает дублирующиеся refresh из каждого парсера.

## Запуск Updater

Один прогон:

```bash
python -m proxy_pipeline.updater --once --deactivate-missing
```

Постоянный режим (каждые 5 минут):

```bash
python -m proxy_pipeline.updater --interval-seconds 300 --deactivate-missing
```

Только выбранные провайдеры:

```bash
python -m proxy_pipeline.updater --interval-seconds 300 --providers proxyline,proxy6
```

Опции:

- `--once` - один цикл обновления и выход
- `--interval-seconds` - интервал в секундах для постоянного режима
- `--providers` - список провайдеров через запятую
- `--deactivate-missing` - помечать отсутствующие прокси как `is_active=false`
- `--lock-file` - lock-файл, не дает запустить второй updater-процесс

## Использование в парсере

```python
from proxy_pipeline import build_default_client

client = build_default_client()
await client.init_db()

# выбор случайного прокси
proxy_url = await client.get_random_proxyline()

# когда клиент больше не нужен
await client.close()
```

## Методы клиента

Класс: `proxy_pipeline.client.ProxyClient`

- `await init_db()`
- `await close()`
- `available_providers()`
- `await refresh_provider(provider_name)`
- `await refresh_proxyline()`
- `await refresh_proxy6()`
- `await refresh_mobileproxyspace()`
- `await refresh_all()`
- `await get_random_proxy(provider=None, as_url=True)`
- `await get_random_proxyline(as_url=True)`
- `await get_random_proxy6(as_url=True)`
- `await get_random_mobileproxyspace(as_url=True)`
- `await ban_proxy(proxy_id=None, server=None, provider=None)`
- `await reload_mobileproxyspace(proxy_key=None, change_ip_url=None, proxy_id=None, user_agent=None)`

## MobileProxySpace

Текущий маппинг `get_my_proxy`:

- `server` <- `proxy_host_ip` + `proxy_http_port`
- `username` <- `proxy_login`
- `password` <- `proxy_pass`
- `change_ip_url` <- `proxy_change_ip_url`
- `proxy_key` <- `proxy_key` или извлекается из `change_ip_url`

Смена IP:

```python
await client.reload_mobileproxyspace(proxy_key="YOUR_PROXY_KEY")
```

или:

```python
await client.reload_mobileproxyspace(
    change_ip_url="https://changeip.mobileproxy.space/?proxy_key=..."
)
```

## Тесты

Запуск:

```bash
pytest -q
```

Интеграционные тесты провайдеров (с реальными API):

```bash
RUN_PROVIDER_INTEGRATION=1 pytest -q tests/test_providers_integration.py
```

Как выбирается БД для тестов (`tests/conftest.py`):

- если есть `TEST_DATABASE_URL`, используется он
- иначе берется `DATABASE_URL` из конфигурации

Если DSN это `postgresql+asyncpg`, для каждого теста создается отдельная схема `test_<uuid>`:

- создаются таблицы в этой схеме
- по завершении теста схема удаляется через `DROP SCHEMA ... CASCADE`

## Структура

- `proxy_pipeline/providers` - адаптеры API провайдеров
- `proxy_pipeline/pipeline.py` - синхронизация с БД
- `proxy_pipeline/repository.py` - работа с моделями прокси
- `proxy_pipeline/client.py` - high-level API для парсеров
- `tests` - тесты
