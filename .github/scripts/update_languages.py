#!/usr/bin/env python3
"""Update the language breakdown in README.md.

Sums the bytes per language that GitHub reports for each public repository
and writes a small text chart between the README markers.

Optional environment variable:
  GITHUB_TOKEN  token for the GitHub API (higher rate limit).
"""

import json
import os
import sys
import urllib.request
from collections import Counter
from pathlib import Path

OWNER = "lorenzoyang"
TOP_N = 8
BAR_WIDTH = 20
EXCLUDED_REPOS = {"lorenzoyang"}
# Markup, styling and build files: not counted as programming languages.
EXCLUDED_LANGS = {
    "HTML", "CSS", "SCSS", "Typst", "TeX", "Makefile", "Shell",
    "PowerShell", "Batchfile", "Dockerfile", "CMake",
}

README = Path(__file__).resolve().parents[2] / "README.md"
START = "<!-- languages:start -->"
END = "<!-- languages:end -->"
API = "https://api.github.com"


def get(url, token):
    request = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "readme-languages-script",
    })
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def list_repos():
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    base = f"{API}/users/{OWNER}/repos?type=owner&per_page=100"

    repos, page = [], 1
    while True:
        batch = get(f"{base}&page={page}", token)
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    repos = [
        repo for repo in repos
        if not repo["fork"] and not repo["archived"] and repo["name"] not in EXCLUDED_REPOS
    ]
    return repos, token


def count_languages(repos, token):
    totals = Counter()
    for repo in repos:
        for language, size in get(repo["languages_url"], token).items():
            if language not in EXCLUDED_LANGS:
                totals[language] += size
    return totals


def render(totals, newline):
    total = sum(totals.values())
    if total == 0:
        sys.exit("No language data found.")

    ranked = totals.most_common()
    if len(ranked) > TOP_N + 1:
        rows = ranked[:TOP_N] + [("Other", sum(size for _, size in ranked[TOP_N:]))]
    else:
        rows = ranked

    width = max(len(name) for name, _ in rows)
    lines = []
    for name, size in rows:
        share = size / total
        filled = round(share * BAR_WIDTH)
        bar = "█" * filled + "░" * (BAR_WIDTH - filled)
        lines.append(f"{name:<{width}}  {bar}  {share * 100:5.1f}%")
    return newline.join(["```text", *lines, "```"])


def main():
    with open(README, encoding="utf-8", newline="") as file:
        text = file.read()
    newline = "\r\n" if "\r\n" in text else "\n"

    start = text.find(START)
    end = text.find(END, start)
    if start == -1 or end == -1:
        sys.exit(f"Markers {START} / {END} not found in README.md")

    repos, token = list_repos()
    chart = render(count_languages(repos, token), newline)
    updated = text[:start] + START + newline + chart + newline + text[end:]

    if updated == text:
        print(f"README.md unchanged ({len(repos)} repositories).")
        return
    with open(README, "w", encoding="utf-8", newline="") as file:
        file.write(updated)
    print(f"README.md updated ({len(repos)} repositories).")


if __name__ == "__main__":
    main()
