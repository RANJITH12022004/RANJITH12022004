#!/usr/bin/env python3
"""Generate a hen-laying contribution SVG from the GitHub contribution calendar."""

from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

USERNAME = os.environ.get("GITHUB_USER_NAME", "RANJITH12022004")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT_DIR = Path(os.environ.get("OUT_DIR", "dist"))

CELL = 12
GAP = 3
STEP = CELL + GAP
PAD_X = 28
PAD_Y = 52
WEEKS = 53
DAYS = 7

EMPTY = "#161b22"
LEVELS = ["#0e4429", "#006d32", "#26a641", "#39d353"]


def fetch_weeks() -> list[list[dict]]:
    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar {
            weeks {
              contributionDays {
                contributionCount
                color
                date
              }
            }
          }
        }
      }
    }
    """
    payload = json.dumps({"query": query, "variables": {"login": USERNAME}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "ranjith-hen-generator",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        data = json.load(resp)
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return weeks[-WEEKS:]


def level_for(count: int) -> int:
    if count <= 0:
        return 0
    if count <= 2:
        return 1
    if count <= 5:
        return 2
    if count <= 9:
        return 3
    return 4


def hen_svg(cx: float, cy: float) -> str:
    return f"""
  <g transform="translate({cx:.1f},{cy:.1f})">
    <ellipse cx="0" cy="2.2" rx="8.4" ry="5.8" fill="#f8fafc"/>
    <circle cx="6.8" cy="-1.8" r="3.8" fill="#f8fafc"/>
    <circle cx="8.1" cy="-2.4" r="0.75" fill="#0f172a"/>
    <path d="M10.2 -1.6 L13.4 -0.1 L10.2 1 Z" fill="#fb923c"/>
    <path d="M-5.8 0.2 Q-10.2 -4.4 -7.6 3.6 Z" fill="#e2e8f0"/>
    <path d="M1.2 -6.2 L2.4 -10.2 L4.2 -6.6 Z" fill="#fde68a"/>
    <ellipse cx="-1.6" cy="7.2" rx="2.3" ry="1.2" fill="#fb923c"/>
    <ellipse cx="2.8" cy="7.2" rx="2.3" ry="1.2" fill="#fb923c"/>
    <circle cx="-2.2" cy="1.2" r="1.4" fill="#39d353" opacity="0.9"/>
  </g>"""


def build_svg(weeks: list[list[dict]]) -> str:
    width = PAD_X * 2 + WEEKS * STEP - GAP
    height = PAD_Y + DAYS * STEP + 28

    active: list[tuple[int, int, int, float, float]] = []
    rects = []
    for wi, week in enumerate(weeks):
        days = week["contributionDays"]
        for di in range(DAYS):
            day = days[di] if di < len(days) else {"contributionCount": 0}
            count = int(day.get("contributionCount") or 0)
            x = PAD_X + wi * STEP
            y = PAD_Y + di * STEP
            lvl = level_for(count)
            fill = EMPTY if lvl == 0 else LEVELS[lvl - 1]
            rects.append(
                f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{EMPTY}" data-fill="{fill}" class="egg" data-i="{len(active) if lvl else -1}"/>'
            )
            if lvl:
                active.append((wi, di, lvl, x + CELL / 2, y + CELL / 2))

    # Hen walks through active cells in reading order, laying eggs.
    path_d = []
    for i, (_, _, _, x, y) in enumerate(active):
        cmd = "M" if i == 0 else "L"
        path_d.append(f"{cmd}{x:.1f},{y:.1f}")
    path = " ".join(path_d) if path_d else f"M{PAD_X},{PAD_Y}"

    duration = max(18.0, min(42.0, 0.18 * max(len(active), 1) + 12))
    egg_css = []
    for i, (_, _, lvl, _, _) in enumerate(active):
        start = (i / max(len(active), 1)) * 100
        end = min(100, start + 1.6)
        fill = LEVELS[lvl - 1]
        egg_css.append(
            f".egg[data-i='{i}']{{animation: lay{i} {duration:.2f}s linear infinite}}"
            f"@keyframes lay{i}{{0%,{start:.2f}%{{fill:{EMPTY}}} {end:.2f}%,100%{{fill:{fill}}}}}"
        )

    hen_dur = duration
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Hen laying contribution commits">
  <title>Hen laying commits</title>
  <defs>
    <style>
      text {{ font-family: Segoe UI, Helvetica, Arial, sans-serif; }}
      .label {{ fill: #8b9cb0; font-size: 13px; }}
      .title {{ fill: #67e8f9; font-size: 15px; font-weight: 600; letter-spacing: 0.08em; }}
      {''.join(egg_css)}
      @media (prefers-reduced-motion: reduce) {{
        .egg {{ animation: none !important; }}
        #hen {{ display: none; }}
      }}
    </style>
  </defs>
  <rect width="100%" height="100%" rx="16" fill="#0d1117"/>
  <text x="{PAD_X}" y="26" class="title">HEN LAYS COMMITS</text>
  <text x="{width - PAD_X}" y="26" text-anchor="end" class="label">green eggs = your contribution days</text>
  <g id="grid">
    {''.join(rects)}
  </g>
  <path id="hen-path" d="{path}" fill="none" stroke="none"/>
  <g id="hen">
    {hen_svg(0, 0)}
    <animateMotion dur="{hen_dur:.2f}s" repeatCount="indefinite" rotate="auto">
      <mpath href="#hen-path"/>
    </animateMotion>
  </g>
</svg>
"""


def main() -> None:
    if not TOKEN:
        raise SystemExit("GITHUB_TOKEN is required")
    weeks = fetch_weeks()
    empty_week = {"contributionDays": [{"contributionCount": 0} for _ in range(DAYS)]}
    while len(weeks) < WEEKS:
        weeks.insert(0, empty_week)
    svg = build_svg(weeks[-WEEKS:])
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "github-hen.svg").write_text(svg, encoding="utf-8")
    (OUT_DIR / "github-hen-dark.svg").write_text(svg, encoding="utf-8")
    print(f"Wrote {OUT_DIR / 'github-hen.svg'} ({len(svg)} bytes)")


if __name__ == "__main__":
    main()
