"""Polite HTTP client with robots.txt enforcement, per-domain delay, and hourly caps."""

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
import re
import time
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

from app.core.config import settings


class PoliteClientError(Exception):
    """Base error raised by PoliteHttpClient policy or network checks."""


class RobotsDisallowedError(PoliteClientError):
    """Raised when robots.txt forbids access or cannot be safely verified."""


class HourlyRateLimitExceededError(PoliteClientError):
    """Raised when per-domain hourly request quota is exhausted."""


class CircuitBreakerOpenError(PoliteClientError):
    """Raised when the retailer's circuit breaker is open."""


class UpstreamFetchError(PoliteClientError):
    """Raised when an HTTP fetch returns an error status or fails at transport level."""


@dataclass(slots=True)
class _RobotsCacheEntry:
    parser: RobotFileParser
    raw_lines: list[str]
    allowed_base: bool
    expires_at: float


def _normalize_agent_name(user_agent: str) -> str:
    return user_agent.split("/", 1)[0].strip().lower()


def _compile_robots_pattern(pattern: str) -> re.Pattern[str]:
    anchored_end = pattern.endswith("$")
    core = pattern[:-1] if anchored_end else pattern
    escaped_parts = [re.escape(part) for part in core.split("*")]
    regex = "^" + ".*".join(escaped_parts) + ("$" if anchored_end else "")
    return re.compile(regex)


def _evaluate_wildcard_rules(
    raw_lines: list[str], user_agent: str, path_and_query: str
) -> bool | None:
    """Evaluate RFC-9309 wildcard Allow/Disallow rules (* and $) missing in stdlib robotparser."""
    agent_token = _normalize_agent_name(user_agent)
    groups: list[tuple[list[str], list[tuple[str, str]]]] = []
    current_agents: list[str] = []
    current_rules: list[tuple[str, str]] = []

    for raw_line in raw_lines:
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        field, value = line.split(":", 1)
        key = field.strip().lower()
        val = value.strip()
        if key == "user-agent":
            if current_rules:
                groups.append((current_agents, current_rules))
                current_agents = []
                current_rules = []
            current_agents.append(val.lower())
        elif key in ("allow", "disallow") and current_agents:
            current_rules.append((key, val))

    if current_agents or current_rules:
        groups.append((current_agents, current_rules))

    specific_rules: list[tuple[str, str]] = []
    wildcard_rules: list[tuple[str, str]] = []
    for agents, rules in groups:
        if any(a != "*" and a in agent_token for a in agents):
            specific_rules.extend(rules)
        elif "*" in agents:
            wildcard_rules.extend(rules)

    active_rules = specific_rules or wildcard_rules
    if not active_rules:
        return None

    best_match: tuple[int, bool] | None = None
    for directive, pattern in active_rules:
        if not pattern:
            continue
        if "*" not in pattern and not pattern.endswith("$"):
            continue
        if _compile_robots_pattern(pattern).search(path_and_query):
            specificity = len(pattern.rstrip("$"))
            allowed = directive == "allow"
            if best_match is None or specificity > best_match[0] or (
                specificity == best_match[0] and allowed and not best_match[1]
            ):
                best_match = (specificity, allowed)

    return best_match[1] if best_match is not None else None


class PoliteHttpClient:
    """Synchronous HTTP client enforcing D-002 and ETHICS.md scraping politeness rules."""

    def __init__(
        self,
        *,
        http_client: httpx.Client | None = None,
        user_agent: str | None = None,
        robots_ttl_seconds: int | None = None,
        default_min_delay_seconds: int | None = None,
        default_max_requests_per_hour: int | None = None,
        clock: Callable[[], float] | None = None,
        sleep_fn: Callable[[float], None] | None = None,
    ) -> None:
        self.user_agent = user_agent or settings.USER_AGENT
        self.robots_ttl_seconds = (
            robots_ttl_seconds
            if robots_ttl_seconds is not None
            else settings.ROBOTS_CACHE_TTL_HOURS * 3600
        )
        self.default_min_delay_seconds = max(
            default_min_delay_seconds or settings.DEFAULT_MIN_DELAY_SECONDS, 10
        )
        self.default_max_requests_per_hour = min(
            default_max_requests_per_hour or settings.DEFAULT_MAX_REQUESTS_PER_HOUR, 30
        )
        self._clock = clock or time.monotonic
        self._sleep = sleep_fn or time.sleep
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(timeout=15.0, follow_redirects=True)
        self._robots_cache: dict[str, _RobotsCacheEntry] = {}
        self._last_request_at: dict[str, float] = {}
        self._hourly_history: dict[str, deque[float]] = {}

    def close(self) -> None:
        """Close the underlying httpx.Client if owned by this instance."""
        if self._owns_client:
            self._client.close()

    def _get_robots_entry(self, url: str) -> _RobotsCacheEntry:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        now = self._clock()
        cached = self._robots_cache.get(domain)
        if cached is not None and cached.expires_at > now:
            return cached

        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = RobotFileParser()
        try:
            resp = self._client.get(robots_url, headers={"User-Agent": self.user_agent})
        except httpx.HTTPError:
            entry = _RobotsCacheEntry(
                parser=rp,
                raw_lines=[],
                allowed_base=False,
                expires_at=now + self.robots_ttl_seconds,
            )
            self._robots_cache[domain] = entry
            return entry

        content_type = resp.headers.get("Content-Type", "").lower()
        body = resp.text or ""
        looks_like_html = "text/html" in content_type or "<html" in body.lower()[:256]
        if resp.status_code != 200 or looks_like_html:
            entry = _RobotsCacheEntry(
                parser=rp,
                raw_lines=[],
                allowed_base=False,
                expires_at=now + self.robots_ttl_seconds,
            )
            self._robots_cache[domain] = entry
            return entry

        lines = body.splitlines()
        rp.parse(lines)
        entry = _RobotsCacheEntry(
            parser=rp,
            raw_lines=lines,
            allowed_base=True,
            expires_at=now + self.robots_ttl_seconds,
        )
        self._robots_cache[domain] = entry
        return entry

    def is_allowed_by_robots(self, url: str) -> bool:
        """Return True iff cached/fetched robots.txt permits fetching url."""
        entry = self._get_robots_entry(url)
        if not entry.allowed_base:
            return False

        parsed = urlparse(url)
        path_and_query = parsed.path or "/"
        if parsed.query:
            path_and_query = f"{path_and_query}?{parsed.query}"

        wildcard_decision = _evaluate_wildcard_rules(
            entry.raw_lines, self.user_agent, path_and_query
        )
        if wildcard_decision is False:
            return False

        return entry.parser.can_fetch(self.user_agent, url)

    def fetch(
        self,
        url: str,
        *,
        min_delay_seconds: int | None = None,
        max_requests_per_hour: int | None = None,
        circuit_breaker_open: bool = False,
    ) -> httpx.Response:
        """Politely fetch a URL after checking circuit breaker, robots.txt, rate cap, and delay."""
        if circuit_breaker_open:
            raise CircuitBreakerOpenError(f"Circuit breaker is open for {url}")

        if not self.is_allowed_by_robots(url):
            raise RobotsDisallowedError(f"robots.txt blocks access to {url}")

        domain = urlparse(url).netloc.lower()
        effective_delay = max(
            min_delay_seconds if min_delay_seconds is not None else self.default_min_delay_seconds,
            10,
        )
        effective_cap = min(
            max_requests_per_hour
            if max_requests_per_hour is not None
            else self.default_max_requests_per_hour,
            30,
        )

        now = self._clock()
        history = self._hourly_history.setdefault(domain, deque())
        cutoff = now - 3600.0
        while history and history[0] <= cutoff:
            history.popleft()

        if len(history) >= effective_cap:
            raise HourlyRateLimitExceededError(
                f"Hourly request limit ({effective_cap}/h) reached for {domain}"
            )

        last_ts = self._last_request_at.get(domain)
        if last_ts is not None:
            elapsed = now - last_ts
            if elapsed < effective_delay:
                self._sleep(effective_delay - elapsed)
                now = self._clock()

        try:
            response = self._client.get(url, headers={"User-Agent": self.user_agent})
        except httpx.HTTPError as exc:
            raise UpstreamFetchError(f"HTTP transport error for {url}: {exc}") from exc

        recorded_now = self._clock()
        self._last_request_at[domain] = recorded_now
        history.append(recorded_now)

        if response.status_code >= 400:
            raise UpstreamFetchError(
                f"Upstream returned HTTP {response.status_code} for {url}"
            )
        return response
