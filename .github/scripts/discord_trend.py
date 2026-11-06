#!/usr/bin/env python3
"""가장 최근 트렌드 리포트의 TOP 5와 추천 조합을 디스코드 웹훅으로 보낸다.

환경 변수
- DISCORD_WEBHOOK_URL: 디스코드 웹훅 주소 (GitHub Secret). 없으면 실패한다.
- DRY_RUN=1: 보내지 않고 보낼 내용만 출력한다.
- GITHUB_REPOSITORY, GITHUB_SHA: 있으면 리포트 링크를 붙인다.
"""
import glob
import json
import os
import re
import sys
import urllib.parse
import urllib.request

REPORT_GLOB = "20_블로그소재/*트렌드 리포트.md"


def clean(cell: str) -> str:
    """표 칸의 굵게 표시 등을 걷어낸다."""
    return cell.replace("**", "").strip()


def section(text: str, heading: str) -> str:
    """`## heading` 아래 본문을 다음 `## ` 전까지 돌려준다."""
    m = re.search(rf"^## {re.escape(heading)}[^\n]*\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    return m.group(1).strip() if m else ""


def parse_top(text: str) -> list[dict]:
    rows = [l for l in section(text, "추천 TOP 5").splitlines() if l.strip().startswith("|")]
    if len(rows) < 3:
        return []
    split = lambda l: [c.strip() for c in l.strip().strip("|").split("|")]
    header = split(rows[0])

    def col(*names):
        for i, h in enumerate(header):
            if any(n in h for n in names):
                return i
        return None

    idx = {
        "rank": col("순위"),
        "topic": col("주제"),
        "category": col("카테고리"),
        "keyword": col("키워드"),
        "score": col("점수"),
        "reason": col("이유"),
        "status": col("신규", "지속", "구분", "상태"),
    }
    items = []
    for line in rows[2:]:
        cells = split(line)
        get = lambda k: clean(cells[idx[k]]) if idx[k] is not None and idx[k] < len(cells) else ""
        total = re.search(r"=\s*(\d+)", get("score"))
        items.append({
            "rank": get("rank"),
            "topic": get("topic"),
            "category": get("category"),
            "keyword": get("keyword"),
            "score": total.group(1) if total else get("score"),
            "reason": get("reason"),
            "status": get("status"),
        })
    return items


def build_payload(path: str) -> dict:
    text = open(path, encoding="utf-8").read()
    date = os.path.basename(path)[:10]
    items = parse_top(text)
    if not items:
        raise SystemExit(f"TOP 5 표를 찾지 못했습니다: {path}")

    lines = []
    for it in items:
        head = f"**{it['rank']}. {it['topic']}**"
        meta = " · ".join(x for x in [it["category"], f"{it['score']}점" if it["score"] else "", it["status"]] if x)
        lines.append(f"{head}\n{meta}")
        if it["reason"]:
            lines.append(f"└ {it['reason']}")
        if it["keyword"]:
            lines.append(f"🔎 {it['keyword']}")
        lines.append("")

    embed = {
        "title": f"{date} 블로그 소재 후보 TOP {len(items)}",
        "description": "\n".join(lines).strip()[:4000],
        "color": 0x03C75A,
        "footer": {"text": "쓸 주제를 고르면 Claude Code에서 /blog-trend 로 소재 노트를 만들어요"},
    }
    combo = section(text, "이번 주 추천 조합")
    if combo:
        embed["fields"] = [{"name": "이번 주 추천 조합", "value": combo[:1000]}]

    repo, sha = os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GITHUB_SHA")
    if repo and sha:
        embed["url"] = f"https://github.com/{repo}/blob/{sha}/{urllib.parse.quote(path)}"

    return {"username": "블로그 트렌드", "embeds": [embed]}


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if not path:
        reports = sorted(glob.glob(REPORT_GLOB))
        if not reports:
            raise SystemExit("트렌드 리포트가 없습니다.")
        path = reports[-1]

    payload = build_payload(path)

    if os.environ.get("DRY_RUN"):
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook:
        raise SystemExit("DISCORD_WEBHOOK_URL이 비어 있습니다. GitHub Secret을 등록하세요.")

    req = urllib.request.Request(
        webhook,
        data=json.dumps(payload).encode("utf-8"),
        # 기본 urllib User-Agent는 디스코드가 403으로 막는다.
        headers={"Content-Type": "application/json", "User-Agent": "blog-trend-notifier/1.0"},
    )
    with urllib.request.urlopen(req, timeout=20) as res:
        print(f"디스코드 전송 완료 ({res.status}): {path}")


if __name__ == "__main__":
    main()
