#!/usr/bin/env python3

import re
import sys
from pathlib import Path
from typing import List, Optional, Dict, Set
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, Future
from urllib.parse import urlparse
from http.client import HTTPResponse
import threading

URL_RE: re.Pattern[str] = re.compile(r'https?://[^\s)>\]]+')

TIMEOUT: int = 3
MAX_WORKERS: int = 10

SKIP_HOSTS: Set[str] = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
}

checked_urls: Dict[str, Optional[str]] = {}
checked_urls_lock = threading.Lock()


def extract_urls(text: str) -> List[str]:
    return URL_RE.findall(text)


def should_skip(url: str) -> bool:
    try:
        parsed = urlparse(url)
        host: Optional[str] = parsed.hostname
        if host is None:
            return True
        return host in SKIP_HOSTS
    except Exception:
        return True


def build_opener(url: str) -> urllib.request.OpenerDirector:
    proxies = urllib.request.getproxies()
    proxy_handler = urllib.request.ProxyHandler(proxies)
    return urllib.request.build_opener(proxy_handler)


def request_url(url: str, method: str) -> Optional[int]:
    opener: urllib.request.OpenerDirector = build_opener(url)
    req: urllib.request.Request = urllib.request.Request(url, method=method)

    with opener.open(req, timeout=TIMEOUT) as response:
        resp: HTTPResponse = response  # typing hint
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
        if status is not None and status >= 400:
            result = f"{url} -> HTTP {status}"

    except urllib.error.HTTPError as e:
        if e.code == 404:
            result = f"{url} -> HTTP 404"
        else:
            try:
                status = request_url(url, "GET")
                if status is not None and status >= 400:
                    result = f"{url} -> HTTP {status}"
            except urllib.error.HTTPError as e2:
                result = f"{url} -> HTTP {e2.code}"
            except Exception:
                result = None

    except Exception:
        result = None  # timeout / ignored

    with checked_urls_lock:
        checked_urls[url] = result
    return result


def check_file(path: Path) -> int:
    text: str = path.read_text(encoding="utf-8", errors="ignore")
    urls: set[str] = set(extract_urls(text))

    errors: List[str] = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures: Dict[Future[Optional[str]], str] = {
            executor.submit(check_url, url): url for url in urls
        }

        for future in futures:
            result: Optional[str] = future.result()
            if result is not None:
                errors.append(f"{path}: {result}")

    for err in errors:
        print(err)

    return 1 if errors else 0


def main() -> int:
    files: List[Path] = [
        Path(p) for p in sys.argv[1:] if "readme" in p.lower()
    ]

    if not files:
        return 0

    exit_code: int = 0
    for file in files:
        exit_code |= check_file(file)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
