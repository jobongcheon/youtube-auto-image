"""메모장으로 쓴 보고서 초안을 읽어 구조로 바꾼다.

형식은 보고서에 실제로 찍히는 모양 그대로다. 기호만 맞게 치면 된다.

    제목: 총장님, 교육부 방문 계획(안)
    날짜: '24. 6. 14.(금)
    부서: 총무과
    개요: (있으면 제목 아래 개요 상자로. 없으면 생략)

    □ 방문 개요
    ○ (목적) 중앙부처와의 **소통 강화** 및 건의사항 전달
    - 세부 내용
    · 더 세부
    ※ 참고 (중고딕으로 작게)
    | 시간 | 주요 내용 | 비고 |
    | 06:40~10:15 | 학교 출발 | |
    붙임: 현장 사진 1부.

맨 윗부분의 '키: 값' 줄은 머리 정보, 그 아래부터가 본문이다.
빈 줄과 '#' 으로 시작하는 줄(메모)은 무시한다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import style

HEADER_KEYS = {"제목": "title", "날짜": "date", "부서": "dept", "개요": "summary"}
ROMAN_RE = re.compile(r"^((?:[IVX]+|[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]))\s*\.?\s+(.+)$")


@dataclass
class Block:
    kind: str  # roman | heading | bullet | table | text | attach
    text: str = ""
    mark: str = ""
    level: int = 0
    rows: list[list[str]] = field(default_factory=list)


@dataclass
class Report:
    title: str = ""
    date: str = ""
    dept: str = ""
    summary: str = ""
    blocks: list[Block] = field(default_factory=list)


class OutlineError(ValueError):
    pass


def _bullet(line: str):
    head, _, rest = line.partition(" ")
    head = style.BULLET_ALIASES.get(head, head)
    if head in style.BULLETS and rest.strip():
        return head, rest.strip()
    if head in style.ARROWS and rest.strip():
        return head, rest.strip()
    return None


def _row(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse(text: str) -> Report:
    rep = Report()
    in_header = True
    table: Block | None = None

    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line.startswith("|"):
            table = None
        if not line or line.startswith("#"):
            continue

        if in_header:
            key, sep, val = line.partition(":")
            if sep and key.strip() in HEADER_KEYS:
                setattr(rep, HEADER_KEYS[key.strip()], val.strip())
                continue
            in_header = False

        if line.startswith("|"):
            cells = _row(line)
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                continue  # 마크다운 표의 |---|---| 구분줄
            if table is None:
                table = Block("table")
                rep.blocks.append(table)
            elif len(cells) != len(table.rows[0]):
                raise OutlineError(
                    f"{lineno}번째 줄: 표의 칸 수가 {len(cells)}개인데 첫 줄은 {len(table.rows[0])}개입니다")
            table.rows.append(cells)
            continue

        if line[0] in style.HEADING_MARKS:
            rep.blocks.append(Block("heading", line[1:].strip(), mark=line[0]))
            continue

        m = ROMAN_RE.match(line)
        if m:
            rep.blocks.append(Block("roman", m.group(2), mark=m.group(1)))
            continue

        if line.startswith("붙임"):
            rep.blocks.append(Block("attach", line.split(":", 1)[-1].strip() if ":" in line else line[2:].strip()))
            continue

        b = _bullet(line)
        if b:
            mark, body = b
            level = style.BULLETS[mark][0] if mark in style.BULLETS else style.BULLETS["-"][0]
            rep.blocks.append(Block("bullet", body, mark=mark, level=level))
            continue

        rep.blocks.append(Block("text", line))

    if not rep.title:
        raise OutlineError("첫 줄에 '제목: ...' 이 있어야 합니다")
    return rep


def dump(rep: Report) -> str:
    """구조를 다시 초안 글로. 엑셀에서 뽑은 보고서를 사람이 고칠 수 있게 남길 때 쓴다."""
    out = [f"제목: {rep.title}"]
    if rep.date:
        out.append(f"날짜: {rep.date}")
    if rep.dept:
        out.append(f"부서: {rep.dept}")
    if rep.summary:
        out.append(f"개요: {rep.summary}")
    for b in rep.blocks:
        if b.kind == "heading":
            out += ["", f"{b.mark or '□'} {b.text}"]
        elif b.kind == "roman":
            out += ["", f"{b.mark}. {b.text}"]
        elif b.kind == "bullet":
            out.append(f"{b.mark} {b.text}")
        elif b.kind == "table":
            out += ["| " + " | ".join(r) + " |" for r in b.rows]
        elif b.kind == "attach":
            out += ["", f"붙임: {b.text}"]
        else:
            out.append(b.text)
    return "\n".join(out) + "\n"
