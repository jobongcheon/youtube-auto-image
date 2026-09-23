import datetime as dt
import tempfile
import unittest
import zipfile
from pathlib import Path

from report_auto import leads, outline, writer

DRAFT = """제목: 테스트 보고
날짜: '26. 9. 23.(수)
부서: 공대통합행정실

□ 개요
○ (목적) **소통 강화**
- 세부
o 알파벳 o 도 ○ 로
※ 참고
| 구분 | 내용 |
|---|---|
| 가 | 나 |
붙임: 사진 1부.
"""


class OutlineTest(unittest.TestCase):
    def test_parse(self):
        rep = outline.parse(DRAFT)
        self.assertEqual(rep.title, "테스트 보고")
        self.assertEqual(rep.dept, "공대통합행정실")
        kinds = [b.kind for b in rep.blocks]
        self.assertEqual(kinds, ["heading", "bullet", "bullet", "bullet", "bullet", "table", "attach"])
        self.assertEqual(rep.blocks[3].mark, "○")          # 'o ' 도 ○ 로 받는다
        self.assertEqual(rep.blocks[5].rows, [["구분", "내용"], ["가", "나"]])  # |---| 줄은 건너뜀

    def test_round_trip(self):
        rep = outline.parse(DRAFT)
        again = outline.parse(outline.dump(rep))
        self.assertEqual([(b.kind, b.text, b.rows) for b in rep.blocks],
                         [(b.kind, b.text, b.rows) for b in again.blocks])

    def test_errors(self):
        with self.assertRaises(outline.OutlineError):
            outline.parse("□ 제목 없음")
        with self.assertRaises(outline.OutlineError):
            outline.parse("제목: x\n| a | b |\n| c |")


class WriterTest(unittest.TestCase):
    def test_docx(self):
        with tempfile.TemporaryDirectory() as d:
            path = writer.build(outline.parse(DRAFT), Path(d) / "a.docx")
            xml = zipfile.ZipFile(path).read("word/document.xml").decode()
        self.assertIn("HY헤드라인M", xml)
        self.assertIn("휴먼명조", xml)
        self.assertIn('w:line="480"', xml)   # 15pt × 160% = 24pt = 480 twip, 고정
        self.assertIn("w:tblHeader", xml)
        self.assertIn("끝.", xml)
        self.assertEqual(xml.count("끝."), 1)


def _lead(day, conv=False, rev=0.0, src="Website", agent="A", follow="Completed", status="Connected"):
    return leads.Lead(date=day, agent=agent, source=src, status=status, minutes=10,
                      follow=follow, converted=conv, revenue=rev, region="Midwest",
                      product="CRM Software", ctype="Prospect")


class LeadsTest(unittest.TestCase):
    def test_quarter(self):
        self.assertEqual(leads.parse_quarter("2026-Q2"), (2026, 2))
        self.assertEqual(leads.parse_quarter("26q4"), (2026, 4))
        with self.assertRaises(ValueError):
            leads.parse_quarter("2026-Q5")

    def test_delta(self):
        self.assertEqual(leads.delta(7.04, 6.94, "%p"), "▲0.1%p")   # 찍힌 값 7.0 − 6.9
        self.assertEqual(leads.delta(100, 100), "동일")
        self.assertEqual(leads.delta(90, 100), "▼10.0%")
        self.assertEqual(leads.delta(1, 0), "비교 불가")

    def test_report(self):
        data = [
            _lead(dt.date(2026, 1, 5)),
            _lead(dt.date(2026, 4, 1), conv=True, rev=50000, src="Referral", agent="B"),
            _lead(dt.date(2026, 5, 2), follow="Pending", status="Interested"),
            _lead(dt.date(2026, 6, 30)),
        ]
        rep = leads.report(data, dept="행정실", today=dt.date(2026, 9, 23))
        self.assertEqual(rep.title, "2026년 2분기 상담 실적 현황 보고")
        self.assertEqual(rep.date, "'26. 9. 23.(수)")
        text = outline.dump(rep)
        self.assertIn("총 **3건**", text)
        self.assertIn("**1건 전환**", text)
        self.assertIn("| 계 | 3 | 1 | 33.3% | 50 |", text)
        self.assertIn("관심 표명·회신 요청 고객 **1건**", text)
        with self.assertRaises(leads.DataError):
            leads.report(data, quarter=(2025, 1))

    def test_load_by_header_name(self):
        import openpyxl

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Customer_Data"
        cols = list(leads.COLS.values())[::-1]  # 열 순서를 뒤집어도 이름으로 찾는다
        ws.append(cols)
        row = {"Call Date": "2026-04-02", "Agent Name": "A", "Lead Source": "Website",
               "Call Status": "Connected", "Call Duration (Min)": 5, "Follow-up Status": "Pending",
               "Conversion Status": "Converted", "Revenue Generated": 1234.5, "Region": "Midwest",
               "Product/Service": "CRM Software", "Customer Type": "Prospect"}
        ws.append([row[c] for c in cols])
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.xlsx"
            wb.save(p)
            got = leads.load(p)
        self.assertEqual(len(got), 1)
        self.assertTrue(got[0].converted)
        self.assertEqual(got[0].date, dt.date(2026, 4, 2))


if __name__ == "__main__":
    unittest.main()
