import aiohttp
import socket
import logging
import asyncio
from random import choice
from proxies_config import PROXYLINE, PROXY6
from urllib.parse import quote
logger = logging.getLogger(__name__)

class ProxiesHandler:
    def __init__(self):
        self.logger = logger
        self.proxies = []
        self.banned_proxies = []

    async def get_proxies_proxyline(self) -> list:
        result = []
        PROXIES_URL = PROXYLINE["proxies_url"]
        PROXIES_PARAMS = PROXYLINE["proxies_params"]
        for i in range(4):
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15), headers={"Accept":"application/json"}, connector=aiohttp.TCPConnector(family=socket.AF_INET)) as s:
                    async with s.get(PROXIES_URL, params=PROXIES_PARAMS) as r:
                        r.raise_for_status()
                        data = await r.json(content_type=None)
                        ps = data.get("results") or []
                        result = [{"server": f"http://{p['ip']}:{p['port_http']}", "username": p["username"], "password": p["password"]} for p in ps if all(k in p for k in ("ip","port_http","username","password"))]
                        self.proxies = result
                        self.logger.info("Всего получено прокси - %d", len(result))
                        return result
            except Exception as e:
                self.logger.warning("Ошибка получения прокси (попытка %d/4): %s", i+1, e, exc_info=True)
                await asyncio.sleep(0.6 * (2 ** i))
        raise RuntimeError("Не удалось получить прокси после 4 попыток")

    async def get_proxies_proxy6(self):
        API_KEY = PROXY6["api_key"]
        STATE = PROXY6.get("state") or "active"  
        URL = f"https://px6.link/api/{API_KEY}/getproxy"
        params = {"state": STATE}
        for i in range(4):
            try:
                timeout = aiohttp.ClientTimeout(total=15)
                async with aiohttp.ClientSession(timeout=timeout, headers={"Accept": "application/json"}) as s:
                    async with s.get(URL, params=params) as r:
                        r.raise_for_status()
                        data = await r.json(content_type=None)
                        if data.get("status") != "yes":
                            raise RuntimeError(f"Proxy6 API error {data.get('error_id')}: {data.get('error')}")

                        items = data.get("list") or {}
                        # у Proxy6 list может быть словарём с числовыми ключами
                        items_iter = items.values() if isinstance(items, dict) else items

                        result = []
                        for p in items_iter:
                            host = p.get("host")
                            port = p.get("port")
                            user = p.get("user")
                            pwd = p.get("pass")
                            ptype = p.get("type")  # "http" (HTTPS) или "socks"
                            if not all([host, port, user, pwd, ptype]):
                                continue
                            scheme = "socks5" if ptype == "socks" else "http"
                            result.append({
                                "server": f"{scheme}://{host}:{port}",
                                "username": user,
                                "password": pwd,
                            })

                        self.proxies = result
                        self.logger.info("Proxy6: всего получено прокси - %d", len(result))
                        return result

            except Exception as e:
                self.logger.warning("Proxy6: ошибка получения прокси (попытка %d/4): %s", i + 1, e, exc_info=True)
                await asyncio.sleep(0.6 * (2 ** i))

        raise RuntimeError("Proxy6: не удалось получить прокси после 4 попыток")

    def _build_proxy_url(self, p):
        if not p: 
            return None
        server = p['server'].split("://", 1)[-1]
        user = quote(p.get('username', ''), safe='')
        pwd  = quote(p.get('password', ''), safe='')
        return f"http://{user}:{pwd}@{server}"

    def return_random_proxy(self):
        if len(self.proxies):
            p = choice(self.proxies)
            proxy = self._build_proxy_url(p)
            return proxy
        else:
            raise Exception("Вначале загрузите прокси, сейчас self.proxies пуст!")