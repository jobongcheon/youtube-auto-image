"""명령줄 도구.

  작성   메모장 초안(.txt) → 표준 서식 보고서(.docx)
  엑셀   상담 리드 엑셀(.xlsx/.xlsm) → 분기 실적 현황 보고서(.docx + 고칠 수 있는 .txt 초안)

  python -m report_auto 작성 초안.txt
  python -m report_auto 엑셀 고객데이터.xlsm --분기 2026-Q2 --부서 공대통합행정실
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import outline, writer


def _write(rep, out: Path):
    try:
        writer.build(rep, out)
    except PermissionError:
        sys.exit(f"[저장 실패] {out} 이(가) 한글·워드에서 열려 있습니다. 닫고 다시 실행하세요.")
    print(f"보고서: {out}")


def cmd_write(args):
    src = Path(args.초안)
    try:
        text = src.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        text = src.read_text(encoding="cp949")  # 윈도우 메모장 옛 기본값(ANSI)
    try:
        rep = outline.parse(text)
    except outline.OutlineError as exc:
        sys.exit(f"[초안 오류] {exc}")
    _write(rep, Path(args.out) if args.out else src.with_suffix(".docx"))


def cmd_excel(args):
    from . import leads

    try:
        data = leads.load(args.엑셀, args.시트)
        q = leads.parse_quarter(args.분기) if args.분기 else None
        rep = leads.report(data, q, dept=args.부서, top=args.상위)
    except ValueError as exc:
        sys.exit(f"[데이터 오류] {exc}")
    out = Path(args.out) if args.out else Path(args.엑셀).with_name(rep.title.replace(" ", "_") + ".docx")
    draft = out.with_suffix(".txt")
    draft.write_text(outline.dump(rep), encoding="utf-8-sig")
    print(f"초안: {draft}   (고친 뒤 '작성'으로 다시 만들 수 있습니다)")
    _write(rep, out)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="report_auto", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    w = sub.add_parser("작성", aliases=["write"], help="초안 .txt → 보고서 .docx")
    w.add_argument("초안")
    w.add_argument("-o", "--out")
    w.set_defaults(fn=cmd_write)

    e = sub.add_parser("엑셀", aliases=["excel"], help="상담 리드 엑셀 → 실적 현황 보고서")
    e.add_argument("엑셀")
    e.add_argument("--분기", help="예: 2026-Q2 (생략하면 가장 최근 분기)")
    e.add_argument("--부서", default="")
    e.add_argument("--시트", help="기본: Customer_Data")
    e.add_argument("--상위", type=int, default=5, help="상담원 순위 표에 넣을 인원")
    e.add_argument("-o", "--out")
    e.set_defaults(fn=cmd_excel)

    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
