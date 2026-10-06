#!/usr/bin/env python3
"""Discover lecture decks and export them to PDFs with decktape."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "https://zzhang.xyz/teaching/security1-fall26/lectures/"


class AnchorParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        for key, value in attrs:
            if key.lower() == "href" and value:
                self.hrefs.append(value)
                break


def fetch_html(url: str) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; Sec1-Slides-export/1.0)",
        },
    )
    with urlopen(request) as response:  # nosec B310 - fixed URL provided via CLI by repository maintainer
        return response.read().decode("utf-8", errors="replace")


def normalize_lecture_url(base_url: str, href: str) -> str | None:
    href = href.strip()
    if not href or href.startswith("#"):
        return None

    abs_url = urljoin(base_url, href)
    parsed = urlparse(abs_url)
    base = urlparse(base_url)

    if parsed.scheme not in {"http", "https"}:
        return None
    if parsed.netloc != base.netloc:
        return None
    if not parsed.path.startswith(base.path):
        return None

    path = parsed.path
    if not path.endswith("/"):
        return None
    if path == base.path:
        return None

    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


def discover_lecture_urls(base_url: str, index_html: str) -> list[str]:
    parser = AnchorParser()
    parser.feed(index_html)

    seen: set[str] = set()
    result: list[str] = []
    for href in parser.hrefs:
        normalized = normalize_lecture_url(base_url, href)
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def lecture_name(url: str) -> str:
    path_parts = [part for part in urlparse(url).path.split("/") if part]
    name = path_parts[-1] if path_parts else "lecture"
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-")
    return safe or "lecture"


def export_lecture(lecture_url: str, output_file: Path, decktape_bin: str, dry_run: bool) -> int:
    cmd = [decktape_bin]
    if os.environ.get("GITHUB_ACTIONS") == "true":
        cmd.extend(
            [
                "--chrome-arg=--no-sandbox",
                "--chrome-arg=--disable-setuid-sandbox",
            ]
        )
    cmd.extend([lecture_url, str(output_file)])
    if dry_run:
        print("DRY RUN:", " ".join(cmd))
        return 0

    output_file.parent.mkdir(parents=True, exist_ok=True)
    print("Running:", " ".join(cmd))
    completed = subprocess.run(cmd, check=False)
    return completed.returncode


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Lectures index URL")
    parser.add_argument(
        "--output-dir",
        default="slides",
        help="Directory where generated PDFs are written",
    )
    parser.add_argument("--decktape-bin", default="decktape", help="decktape executable")
    parser.add_argument(
        "--index-html-path",
        help="Local HTML file to parse instead of downloading --base-url (useful for testing)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print planned exports without running decktape")
    return parser.parse_args(list(argv))


def main(argv: Iterable[str]) -> int:
    args = parse_args(argv)

    if args.index_html_path:
        index_html = Path(args.index_html_path).read_text(encoding="utf-8")
    else:
        index_html = fetch_html(args.base_url)

    lecture_urls = discover_lecture_urls(args.base_url, index_html)
    if not lecture_urls:
        print(f"No lecture URLs found from {args.base_url}", file=sys.stderr)
        return 1

    print(f"Found {len(lecture_urls)} lecture decks")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    failures = 0
    expected_outputs: set[Path] = set()

    for url in lecture_urls:
        output_file = output_dir / f"{lecture_name(url)}.pdf"
        expected_outputs.add(output_file.resolve())
        rc = export_lecture(url, output_file, args.decktape_bin, args.dry_run)
        if rc != 0:
            failures += 1

    if not args.dry_run:
        for existing_pdf in output_dir.glob("*.pdf"):
            if existing_pdf.resolve() not in expected_outputs:
                print(f"Removing stale PDF: {existing_pdf}")
                existing_pdf.unlink()

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
