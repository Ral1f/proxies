from proxy_pipeline.utils import build_proxy_url, normalize_server


def test_build_proxy_url_with_auth():
    url = build_proxy_url("http", "1.2.3.4:8080", "user", "p@ss")
    assert url == "http://user:p%40ss@1.2.3.4:8080"


def test_build_proxy_url_without_auth():
    url = build_proxy_url("socks5", "1.2.3.4:1080", None, None)
    assert url == "socks5://1.2.3.4:1080"


def test_normalize_server():
    server, scheme = normalize_server("http://1.2.3.4:8080")
    assert server == "1.2.3.4:8080"
    assert scheme == "http"

    server, scheme = normalize_server("1.2.3.4:8080")
    assert server == "1.2.3.4:8080"
    assert scheme == ""
