"""상담 리드 엑셀(Customer_Data) → 실적 현황 보고서.

열 순서가 바뀌어도 되도록 머리글 이름으로 열을 찾는다.
기간은 분기 단위로 자르고, 바로 앞 분기와 비교한다.
"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from .outline import Block, Report

COLS = {
    "date": "Call Date", "agent": "Agent Name", "source": "Lead Source",
    "status": "Call Status", "minutes": "Call Duration (Min)", "follow": "Follow-up Status",
    "conv": "Conversion Status", "revenue": "Revenue Generated", "region": "Region",
    "product": "Product/Service", "ctype": "Customer Type",
}

KO = {
    # 유입 경로
    "Referral": "지인 추천", "Google Ads": "구글 광고", "Facebook Ads": "페이스북 광고",
    "LinkedIn Ads": "링크드인 광고", "Inbound Call": "인바운드 전화", "Website": "홈페이지",
    "Email Campaign": "이메일 캠페인", "Outbound Campaign": "아웃바운드 캠페인",
    # 지역
    "Midwest": "중서부", "Southeast": "남동부", "Southwest": "남서부",
    "Northeast": "북동부", "West Coast": "서부 해안",
    # 상품
    "Business Consulting": "경영 컨설팅", "CRM Software": "CRM 소프트웨어",
    "Digital Marketing Services": "디지털 마케팅", "Cloud Solutions": "클라우드",
    "SaaS Subscription": "SaaS 구독", "Cybersecurity Services": "보안 서비스",
    "Insurance Plan": "보험 상품", "Business Loan": "사업자 대출",
    # 후속 조치
    "Pending": "대기", "Scheduled": "예정", "Completed": "완료", "Not Required": "불필요",
}
WEEKDAY = "월화수목금토일"


class DataError(ValueError):
    pass


@dataclass
class Lead:
    date: dt.date
    agent: str
    source: str
    status: str
    minutes: float
    follow: str
    converted: bool
    revenue: float
    region: str
    product: str
    ctype: str

    @property
    def quarter(self) -> tuple[int, int]:
        return self.date.year, (self.date.month - 1) // 3 + 1


def _as_date(v) -> dt.date:
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    return dt.date.fromisoformat(str(v).strip()[:10])


def load(path: str | Path, sheet: str | None = None) -> list[Lead]:
    import openpyxl  # 엑셀 보고서를 쓸 때만 필요하다

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[sheet] if sheet else next((w for w in wb.worksheets if w.title == "Customer_Data"), wb.worksheets[0])
    rows = ws.iter_rows(values_only=True)
    header = [str(h).strip() if h is not None else "" for h in next(rows)]
    missing = [name for name in COLS.values() if name not in header]
    if missing:
        raise DataError(f"'{ws.title}' 시트에 이 열이 없습니다: {', '.join(missing)}")
    idx = {k: header.index(name) for k, name in COLS.items()}

    out = []
    for n, r in enumerate(rows, 2):
        if r[idx["date"]] is None:
            continue
        try:
            out.append(Lead(
                date=_as_date(r[idx["date"]]),
                agent=str(r[idx["agent"]]), source=str(r[idx["source"]]),
                status=str(r[idx["status"]]), minutes=float(r[idx["minutes"]] or 0),
                follow=str(r[idx["follow"]]),
                converted=str(r[idx["conv"]]).strip().lower() == "converted",
                revenue=float(r[idx["revenue"]] or 0), region=str(r[idx["region"]]),
                product=str(r[idx["product"]]), ctype=str(r[idx["ctype"]]),
            ))
        except (TypeError, ValueError) as exc:
            raise DataError(f"{n}번째 행을 읽을 수 없습니다: {exc}") from exc
    wb.close()
    return out


# ── 집계 ──────────────────────────────────────────────────────

@dataclass
class Stat:
    leads: int = 0
    conv: int = 0
    revenue: float = 0.0

    def add(self, lead: Lead):
        self.leads += 1
        self.conv += lead.converted
        self.revenue += lead.revenue

    @property
    def rate(self) -> float:
        return self.conv / self.leads * 100 if self.leads else 0.0


def _total(leads) -> Stat:
    s = Stat()
    for x in leads:
        s.add(x)
    return s


def _group(leads, key) -> dict[str, Stat]:
    g: dict[str, Stat] = defaultdict(Stat)
    for x in leads:
        g[key(x)].add(x)
    return g


def _prev(q: tuple[int, int]) -> tuple[int, int]:
    y, n = q
    return (y - 1, 4) if n == 1 else (y, n - 1)


def parse_quarter(text: str) -> tuple[int, int]:
    """'2026-Q2', '2026Q2', '26-2' 모두 받는다."""
    t = text.upper().replace(" ", "").replace("Q", "-").replace("--", "-")
    y, _, n = t.partition("-")
    y, n = int(y), int(n)
    if y < 100:
        y += 2000
    if not 1 <= n <= 4:
        raise ValueError(text)
    return y, n


# ── 표기 ──────────────────────────────────────────────────────

def ko(v: str) -> str:
    return KO.get(v, v)


def won(v: float) -> str:
    """금액은 천 단위로. 원본 통화 단위는 엑셀에 적혀 있지 않아 붙이지 않는다."""
    return f"{v / 1000:,.0f}"


def pct(v: float) -> str:
    return f"{v:.1f}%"


def delta(now: float, before: float, unit: str = "") -> str:
    if not before:
        return "비교 불가"
    d = now - before
    if unit == "%p":  # 보고서에 찍힌 소수 첫째 자리끼리 빼야 읽는 사람 계산과 맞는다
        d = round(round(now, 1) - round(before, 1), 1)
    elif round(d / before * 100, 1) == 0:
        d = 0
    if d == 0:
        return "동일"
    sign = "▲" if d > 0 else "▼"
    if unit == "%p":
        return f"{sign}{abs(d):.1f}%p"
    return f"{sign}{abs(d) / before * 100:.1f}%"


def short_date(d: dt.date) -> str:
    return f"'{d:%y}. {d.month}. {d.day}.({WEEKDAY[d.weekday()]})"


def _period(q) -> str:
    return f"{q[0]}년 {q[1]}분기"


def _months(q) -> tuple[dt.date, dt.date]:
    y, n = q
    start = dt.date(y, 3 * n - 2, 1)
    end = dt.date(y + (n == 4), 1 if n == 4 else 3 * n + 1, 1) - dt.timedelta(days=1)
    return start, end


# ── 보고서 ────────────────────────────────────────────────────

def report(leads: list[Lead], quarter: tuple[int, int] | None = None,
           dept: str = "", today: dt.date | None = None, top: int = 5) -> Report:
    if not leads:
        raise DataError("데이터가 비어 있습니다")
    quarter = quarter or max(x.quarter for x in leads)
    cur = [x for x in leads if x.quarter == quarter]
    if not cur:
        have = sorted({x.quarter for x in leads})
        raise DataError(f"{_period(quarter)} 데이터가 없습니다. 있는 기간: "
                        + ", ".join(f"{y}-Q{n}" for y, n in have))
    pq = _prev(quarter)
    prev = [x for x in leads if x.quarter == pq]

    T, P = _total(cur), _total(prev)
    start, end = _months(quarter)
    agents = len({x.agent for x in cur})
    avg_min = sum(x.minutes for x in cur) / len(cur)
    per_conv = T.revenue / T.conv if T.conv else 0

    by_source = sorted(_group(cur, lambda x: x.source).items(), key=lambda kv: -kv[1].rate)
    by_agent = sorted(_group(cur, lambda x: x.agent).items(), key=lambda kv: -kv[1].revenue)
    by_region = sorted(_group(cur, lambda x: x.region).items(), key=lambda kv: -kv[1].revenue)
    by_product = sorted(_group(cur, lambda x: x.product).items(), key=lambda kv: -kv[1].revenue)
    by_month = sorted(_group(cur, lambda x: f"{x.date.month}월").items(),
                      key=lambda kv: int(kv[0][:-1]))

    pending = [x for x in cur if x.follow == "Pending"]
    hot_pending = [x for x in pending if x.status in ("Interested", "Callback Requested") and not x.converted]

    best_src, worst_src = by_source[0], by_source[-1]
    best_agent = by_agent[0]

    rep = Report(
        title=f"{_period(quarter)} 상담 실적 현황 보고",
        date=short_date(today or dt.date.today()),
        dept=dept,
        summary=(f"{_period(quarter)}({start:%Y.%m.%d.}~{end:%m.%d.}) 상담 리드 {T.leads:,}건의 "
                 f"전환 실적과 유입경로·상담원별 성과를 분석하여 보고 드림"),
    )
    B = rep.blocks.append

    B(Block("heading", "실적 개요", mark="□"))
    B(Block("bullet", f"(상담 건수) 총 **{T.leads:,}건**, 상담원 {agents}명, 건당 평균 통화 {avg_min:.1f}분", mark="○", level=1))
    if prev:
        B(Block("bullet", f"전 분기({_period(pq)}) {P.leads:,}건 대비 {delta(T.leads, P.leads)}", mark="-", level=2))
    B(Block("bullet", f"(전환 실적) **{T.conv:,}건 전환**, 전환율 **{pct(T.rate)}**", mark="○", level=1))
    if prev:
        B(Block("bullet", f"전 분기 전환율 {pct(P.rate)} 대비 {delta(T.rate, P.rate, '%p')}", mark="-", level=2))
    B(Block("bullet", f"(매출) 총 **{won(T.revenue)}천**, 전환 1건당 평균 {won(per_conv)}천", mark="○", level=1))
    if prev:
        B(Block("bullet", f"전 분기 {won(P.revenue)}천 대비 {delta(T.revenue, P.revenue)}", mark="-", level=2))

    B(Block("table", rows=[["구분", "상담", "전환", "전환율", "매출(천)"]]
            + [[m, f"{s.leads:,}", f"{s.conv:,}", pct(s.rate), won(s.revenue)] for m, s in by_month]
            + [["계", f"{T.leads:,}", f"{T.conv:,}", pct(T.rate), won(T.revenue)]]))

    B(Block("heading", "유입경로별 전환 현황", mark="□"))
    B(Block("bullet", f"전환율 최고는 **{ko(best_src[0])}**({pct(best_src[1].rate)}), "
                      f"최저는 {ko(worst_src[0])}({pct(worst_src[1].rate)})", mark="○", level=1))
    gap = best_src[1].rate - worst_src[1].rate
    B(Block("bullet", f"두 경로 간 전환율 차이 {gap:.1f}%p", mark="-", level=2))
    B(Block("table", rows=[["유입경로", "상담", "전환", "전환율", "매출(천)"]]
            + [[ko(k), f"{s.leads:,}", f"{s.conv:,}", pct(s.rate), won(s.revenue)] for k, s in by_source]))

    B(Block("heading", "상담원별 실적", mark="□"))
    B(Block("bullet", f"매출 1위 **{best_agent[0]}**: 전환 {best_agent[1].conv}건, "
                      f"매출 {won(best_agent[1].revenue)}천", mark="○", level=1))
    B(Block("bullet", f"상위 {top}명 매출 합계가 전체의 "
                      f"{sum(s.revenue for _, s in by_agent[:top]) / T.revenue * 100:.1f}% 차지"
            if T.revenue else f"상위 {top}명", mark="-", level=2))
    B(Block("table", rows=[["순위", "상담원", "상담", "전환", "전환율", "매출(천)"]]
            + [[str(i), k, f"{s.leads:,}", f"{s.conv:,}", pct(s.rate), won(s.revenue)]
               for i, (k, s) in enumerate(by_agent[:top], 1)]))

    B(Block("heading", "지역·상품별 매출", mark="□"))
    B(Block("bullet", "(지역) " + ", ".join(f"{ko(k)} {won(s.revenue)}천" for k, s in by_region), mark="○", level=1))
    B(Block("bullet", "(상품) 상위 3개 " + ", ".join(f"{ko(k)} {won(s.revenue)}천" for k, s in by_product[:3]),
            mark="○", level=1))

    B(Block("heading", "향후 조치", mark="□"))
    B(Block("bullet", f"(후속 조치) 후속 연락 **대기 {len(pending):,}건** 중 관심 표명·회신 요청 고객 "
                      f"**{len(hot_pending):,}건** 우선 연락", mark="○", level=1))
    B(Block("bullet", f"(유입경로) 전환율이 높은 {ko(best_src[0])} 비중 확대, "
                      f"{ko(worst_src[0])} 경로는 효과 점검", mark="○", level=1))
    B(Block("bullet", "금액 단위: 천(원본 엑셀의 Revenue Generated 기준)", mark="※", level=4))
    return rep
