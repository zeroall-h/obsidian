"""raw/ 노트 중 wiki/log.md 에 아직 기록되지 않은 것을 최신순으로 출력한다.

사용: python -I find_new.py <보관함 루트>
출력: 한 줄에 하나씩 "상태<TAB>수정시각<TAB>raw 상대경로"
  상태 — new(새 노트) | no-frontmatter(frontmatter 없음, 템플릿 미적용 사본일 가능성)
"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
from datetime import datetime

root = sys.argv[1] if len(sys.argv) > 1 else "."
raw_dir = os.path.join(root, "raw")
log_path = os.path.join(root, "wiki", "log.md")

logged = set()
if os.path.exists(log_path):
    with open(log_path, encoding="utf-8") as f:
        for m in re.finditer(r"^- raw: `([^`]+)`", f.read(), re.M):
            logged.add(m.group(1).replace("\\", "/"))

rows = []
for dirpath, _, names in os.walk(raw_dir):
    for name in names:
        if not name.endswith(".md"):
            continue
        full = os.path.join(dirpath, name)
        rel = os.path.relpath(full, root).replace("\\", "/")
        if rel in logged:
            continue
        with open(full, encoding="utf-8") as f:
            has_fm = f.read(4) == "---\n" or False
        rows.append((os.path.getmtime(full), "new" if has_fm else "no-frontmatter", rel))

for mtime, state, rel in sorted(rows, reverse=True):
    stamp = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
    print(f"{state}\t{stamp}\t{rel}")
if not rows:
    print("(인제스트할 새 raw 노트 없음)")
