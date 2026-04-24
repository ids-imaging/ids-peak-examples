#!/usr/bin/env python3

import re
import sys
from pathlib import Path
from typing import Optional, Set
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
from urllib.parse import urlparse
from http.client import HTTPResponse
import threading

URL_RE: re.Pattern[str] = re.compile(r'https?://[^\s)>\]]+')
MD_LINK_RE: re.Pattern[str] = re.compile(r'\[.*?\]\((?!https?://)(.*?)\)')

TIMEOUT: int = 3
MAX_WORKERS: int = 20

SKIP_HOSTS: Set[str] = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
}

checked_urls: dict[str, Optional[str]] = {}
checked_urls_lock = threading.Lock()


def extract_urls(text: str) -> list[str]:
    return URL_RE.findall(text)


def extract_relative_links(text: str) -> list[str]:
    return MD_LINK_RE.findall(text)


def should_skip(url: str) -> bool:
    try:
        host = urlparse(url).hostname
        return host is None or host in SKIP_HOSTS
    except Exception:
        return True


def collect_all_links(files: list[Path]) -> tuple[dict[str, set[Path]], list[tuple[Path, str]]]:
    url_to_files: dict[str, Set[Path]] = {}
    rel_links: list[tuple[Path, str]] = []

    for file in files:
        text = file.read_text(encoding="utf-8", errors="ignore")

        # external URLs
        for url in extract_urls(text):
            url_to_files.setdefault(url, set()).add(file)

        # relative links
        for link in extract_relative_links(text):
            rel_links.append((file, link))

    return url_to_files, rel_links


def check_relative_link(base_path: Path, link: str) -> Optional[str]:
    link = link.split("#")[0].strip()

    if not link:
        return None

    target = (base_path.parent / link).resolve()

    if not target.exists():
        return f"{base_path}: missing file -> {link}"

    return None


def build_opener(url: str) -> urllib.request.OpenerDirector:
    return urllib.request.build_opener(
        urllib.request.ProxyHandler(urllib.request.getproxies())
    )


def request_url(url: str, method: str) -> Optional[int]:
    opener = build_opener(url)
    req = urllib.request.Request(url, method=method)

    with opener.open(req, timeout=TIMEOUT) as response:
        resp: HTTPResponse = response
        return resp.getcode()


def check_url(url: str) -> Optional[str]:
    with checked_urls_lock:
        if url in checked_urls:
            return checked_urls[url]

        if should_skip(url):
            checked_urls[url] = None
            return None

    result: Optional[str] = None

    try:
        status = request_url(url, "HEAD")
        if status and status >= 400:
            result = f"{url} -> HTTP {status}"

    except urllib.error.HTTPError as e:
        if e.code == 404:
            result = f"{url} -> HTTP 404"
        else:
            try:
                status = request_url(url, "GET")
                if status and status >= 400:
                    result = f"{url} -> HTTP {status}"
            except Exception:
                result = None

    except Exception:
        result = None

    with checked_urls_lock:
        checked_urls[url] = result

    return result


def main() -> int:
    files: list[Path] = [
        Path(p) for p in sys.argv[1:] if "readme" in p.lower()
    ]

    if not files:
        return 0

    # COLLECT EVERYTHING
    url_map, rel_links = collect_all_links(files)

    errors: list[str] = []

    # RELATIVE FILE CHECKS
    for file, link in rel_links:
        err = check_relative_link(file, link)
        if err:
            errors.append(err)

    # GLOBAL URL CHECK
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_map: dict[Future[Optional[str]], str] = {
            executor.submit(check_url, url): url
            for url in url_map.keys()
        }

        for future in as_completed(future_map):
            result = future.result()
            if result:
                url = future_map[future]
                for file in url_map[url]:
                    errors.append(f"{file}: {result}")

    for err in errors:
        print(err)

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
