DATABASE_URL = "sqlite+aiosqlite:///proxies.db"

PROXYLINE = {
    "proxies_url": "https://proxyline.example/api/proxies",
    "proxies_params": {
        "page": 1,
        "page_size": 100,
    },
}

PROXY6 = {
    "api_key": "YOUR_PROXY6_KEY",
    "state": "active",
}

MOBILEPROXYSPACE = {
    "api_token": "YOUR_MOBILEPROXYSPACE_TOKEN",
    "base_url": "https://mobileproxy.space/api.html",
    "proxy_ids": ["123", "456"],
    "command": "get_my_proxy",
}

PROXYWING = {
    "file_path": "/path/to/proxywing.txt",
    "protocol": "http",
}
