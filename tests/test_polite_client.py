import httpx
import pytest

from app.core.config import settings
from app.scraping.polite_client import (
    CircuitBreakerOpenError,
    HourlyRateLimitExceededError,
    PoliteHttpClient,
    RobotsDisallowedError,
    UpstreamFetchError,
)


class FakeClock:
    def __init__(self, start: float = 1000.0) -> None:
        self.now = start
        self.sleeps: list[float] = []

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


JDSPORTS_ROBOTS = """User-agent: *
Disallow: /search
Disallow: /aisearch*
Disallow: /cos$
Disallow: /cos/*
Disallow: /login
Disallow: /profil
Allow: /
"""

BUZZ_ROBOTS = """User-agent: *
Disallow: /*?search=
Disallow: /*?SID=
Disallow: /*crawl=no
Allow: /
"""


def _build_client(
    handler,
    clock: FakeClock | None = None,
    robots_ttl_seconds: int = 86400,
) -> tuple[PoliteHttpClient, FakeClock]:
    fake_clock = clock or FakeClock()
    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport)
    client = PoliteHttpClient(
        http_client=http_client,
        user_agent=settings.USER_AGENT,
        robots_ttl_seconds=robots_ttl_seconds,
        clock=fake_clock.time,
        sleep_fn=fake_clock.sleep,
    )
    return client, fake_clock


def test_polite_client_sends_custom_user_agent_and_caches_robots() -> None:
    seen_headers: list[str] = []
    robots_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal robots_calls
        seen_headers.append(request.headers.get("User-Agent", ""))
        if request.url.path == "/robots.txt":
            robots_calls += 1
            return httpx.Response(200, text=JDSPORTS_ROBOTS)
        return httpx.Response(200, text="<html><body>OK</body></html>")

    client, clock = _build_client(handler, robots_ttl_seconds=86400)
    resp1 = client.fetch("https://www.jdsports.ro/nike-air-jordan-1-low-553558-403")
    assert resp1.status_code == 200
    assert robots_calls == 1

    clock.now += 15.0
    resp2 = client.fetch("https://www.jdsports.ro/adidas-campus-00s-hq8708")
    assert resp2.status_code == 200
    # Cached within 24h TTL
    assert robots_calls == 1
    assert all(ua == settings.USER_AGENT for ua in seen_headers)

    # Expired after 24h TTL -> re-fetched
    clock.now += 86401.0
    client.fetch("https://www.jdsports.ro/nike-air-jordan-1-high-dz5485-612")
    assert robots_calls == 2


def test_polite_client_enforces_robots_allowed_vs_blocked_paths() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "www.jdsports.ro" and request.url.path == "/robots.txt":
            return httpx.Response(200, text=JDSPORTS_ROBOTS)
        if request.url.host == "www.buzzsneakers.ro" and request.url.path == "/robots.txt":
            return httpx.Response(200, text=BUZZ_ROBOTS)
        return httpx.Response(200, text="<html>ok</html>")

    client, clock = _build_client(handler)

    # Allowed product URLs
    assert client.is_allowed_by_robots("https://www.jdsports.ro/nike-air-jordan-1-low-553558-403") is True
    assert (
        client.is_allowed_by_robots(
            "https://www.buzzsneakers.ro/pantofi-sport/nike-air-jordan-1-low-553558-403"
        )
        is True
    )

    # Disallowed paths per ETHICS.md
    for blocked_url in (
        "https://www.jdsports.ro/search?q=jordan",
        "https://www.jdsports.ro/cos/checkout",
        "https://www.jdsports.ro/cos",
        "https://www.jdsports.ro/login",
        "https://www.buzzsneakers.ro/pantofi?search=nike",
        "https://www.buzzsneakers.ro/sneakers?SID=123",
    ):
        assert client.is_allowed_by_robots(blocked_url) is False
        with pytest.raises(RobotsDisallowedError):
            client.fetch(blocked_url)


def test_polite_client_fails_closed_on_missing_or_html_robots() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "www.jdsports.ro":
            return httpx.Response(404, text="Not Found")
        return httpx.Response(200, headers={"Content-Type": "text/html"}, text="<html>Home</html>")

    client, _ = _build_client(handler)
    with pytest.raises(RobotsDisallowedError):
        client.fetch("https://www.jdsports.ro/nike-air-jordan-1-low-553558-403")
    with pytest.raises(RobotsDisallowedError):
        client.fetch("https://sizeer.ro/adidas-campus-00s-hq8708")


def test_polite_client_enforces_min_delay_per_domain_and_hourly_cap() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        return httpx.Response(200, text="<html>ok</html>")

    client, clock = _build_client(handler)

    # First request to jdsports needs no delay
    client.fetch("https://www.jdsports.ro/p1")
    assert clock.sleeps == []

    # Second request after only 3s must sleep remaining 7s to honor >=10s delay
    clock.now += 3.0
    client.fetch("https://www.jdsports.ro/p2")
    assert clock.sleeps == [7.0]

    # Different domain does not inherit jdsports's delay
    client.fetch("https://sizeer.ro/p1")
    assert clock.sleeps == [7.0]

    # Exhaust remaining 28 requests in the 30/hour window for jdsports
    for idx in range(28):
        clock.now += 10.0
        client.fetch(f"https://www.jdsports.ro/p{idx + 3}")

    clock.now += 10.0
    with pytest.raises(HourlyRateLimitExceededError):
        client.fetch("https://www.jdsports.ro/p31")

    # Advancing past 1 hour frees the sliding window
    clock.now += 3601.0
    resp = client.fetch("https://www.jdsports.ro/p32")
    assert resp.status_code == 200


def test_polite_client_respects_circuit_breaker_and_upstream_errors() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        return httpx.Response(503, text="Service Unavailable")

    client, _ = _build_client(handler)

    with pytest.raises(CircuitBreakerOpenError):
        client.fetch("https://www.jdsports.ro/p1", circuit_breaker_open=True)

    with pytest.raises(UpstreamFetchError):
        client.fetch("https://www.jdsports.ro/p1", circuit_breaker_open=False)
