"""보고서 표준 서식.

「보고서 작성을 위한 참고 자료」('26. 9. 22., 공대통합행정실) 2~3쪽 표를 그대로 옮겼다.
서식을 바꿀 일이 생기면 이 파일만 고치면 된다.

줄간격 160% 는 한글(HWP) 기준이다. HWP 의 % 는 글자 크기에 곱하는 값이라
워드의 '배수 1.6'(글꼴 높이의 1.6배, 훨씬 넓다)과 다르다. 그래서 글자 크기 × 1.6 을
'고정 간격'으로 넣어 한글에서 보던 모양과 맞춘다.
"""

from __future__ import annotations

from dataclasses import dataclass

# 한글 기본 글꼴. 워드에서 열 때 PC 에 없으면 비슷한 글꼴로 대신 보인다.
# 한글 프로그램이 깔린 PC 에는 셋 다 들어 있다.
HEADLINE = "HY헤드라인M"
MYEONGJO = "휴먼명조"
GOTHIC = "HY중고딕"

LINE_RATIO = 1.6  # 줄간격 160%


@dataclass(frozen=True)
class Font:
    name: str
    size: float  # pt
    before: float = 0  # 문단 위 간격 pt
    after: float = 0  # 문단 아래 간격 pt
    bold: bool = False


# 용지: 여백 위/아래 15mm, 좌/우 20mm, 머리말/꼬리말 10mm
PAGE = {"width_mm": 210, "height_mm": 297,
        "top_mm": 15, "bottom_mm": 15, "left_mm": 20, "right_mm": 20,
        "header_mm": 10, "footer_mm": 10}

TITLE = Font(HEADLINE, 22)                     # 문서제목 글상자
META = Font(MYEONGJO, 12, before=4)            # < '26. 9. 23.(수), 부서 >
SUMMARY = Font(GOTHIC, 15, before=5)           # 개요 글상자
ROMAN = Font(HEADLINE, 17, before=25, after=5)  # I. 첫째 항목 (4~5쪽 이상 보고서)
HEADING = Font(HEADLINE, 16, before=25, after=5)  # □ 본문 큰제목
BODY = Font(MYEONGJO, 15, before=5)            # ○ - · 본문
NOTE = Font(GOTHIC, 13, before=3)              # ※ 참고사항
TABLE = Font(MYEONGJO, 13)                     # 표 안 글씨 (본문보다 조금 작게)
TABLE_CELL_MARGIN_PT = 3                       # 셀 좌·우 여백

# 항목 기호 → (단계, 들여쓰기 칸 수, 글꼴)
# 3쪽 "보고서 분량이 3쪽 이하일 경우": ○ 1칸, - 2칸, · 3칸, ※ 4칸
BULLETS = {
    "○": (1, 1, BODY),
    "-": (2, 2, BODY),
    "·": (3, 3, BODY),
    "※": (4, 4, NOTE),
}
# 입력할 때 흔히 치는 다른 모양도 받아준다
BULLET_ALIASES = {"o": "○", "ㅇ": "○", "◦": "○", "•": "·", "ㆍ": "·", "–": "-", "*": "※"}
# 화살표류는 앞 항목에 딸린 설명이라 '-' 와 같은 깊이로 둔다
ARROWS = ("☞", "⇒", "→")

HEADING_MARKS = ("□", "☐", "◈")

TABLE_HEADER_FILL = "D9D9D9"
EMPHASIS_COLOR = None  # 강조는 굵게만. 강한 원색은 쓰지 않는다 (2쪽)
