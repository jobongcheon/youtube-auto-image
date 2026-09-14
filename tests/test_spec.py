"""스펙과 프롬프트가 원본과 어긋나지 않는지 지킨다.

표준 라이브러리만 쓴다:  python3 -m unittest discover -s tests
"""

import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.prompts import image_mj, image_natural, video
from src.spec import Spec, SpecError

SPEC = Path(__file__).resolve().parent.parent / "spec" / "isunsin.json"


class TestSpec(unittest.TestCase):
    def setUp(self):
        self.spec = Spec.load(SPEC)

    def test_totals(self):
        self.assertEqual(
            self.spec.totals,
            {"blocks": 14, "beats": 51, "images": 183, "videos": 132},
        )

    def test_header_counts_match_beats(self):
        """앵커 - 클립 == 비트 수. 이 항등식이 14블록 복원의 근거다."""
        for block in self.spec.data["blocks"]:
            self.assertEqual(
                block["anchors"] - block["clips"],
                len(block["beats"]),
                f"{block['no']}블록",
            )

    def test_block1_filenames(self):
        self.assertEqual(
            [c.stem for c in self.spec.cuts(1)],
            ["1블-b1-k1", "1블-b1-k2", "1블-b1-k3", "1블-b1-k4",
             "1블-b2-k1", "1블-b2-k2", "1블-b2-k3", "1블-b2-k4",
             "1블-b3-k1", "1블-b3-k2", "1블-b3-k3"],
        )

    def test_mj_prompt_is_byte_identical_to_source(self):
        cuts = self.spec.cuts(1)
        self.assertEqual(
            image_mj(self.spec, cuts[0]),
            "Strait off Hansan Island, open sea battlefield with distant cliffs, "
            "dawn mist, extreme wide establishing shot, pre-dawn blue hour, cold "
            "monochrome, a single faint warm light source in the distance, "
            "조선중기1550-1650, 용머리 장식, 철정(쇠못), 소나무 선체 판자, 참나무 나무못, "
            "[CAST], [LOCK] , [R-PAINT] , [STYLE] --ar 16:9 --sref [SEED] --sw 110 "
            "--no [FORBIDDEN]",
        )
        self.assertIn("progressively closer (2 of 4)", image_mj(self.spec, cuts[1]))
        self.assertIn("closest framing of this beat", image_mj(self.spec, cuts[3]))

    def test_natural_prompt_drops_midjourney_flags(self):
        """나노바나나 프로는 --ar 같은 플래그를 이해하지 못한다."""
        text = image_natural(self.spec, self.spec.cuts(1)[0])
        for flag in ("--ar", "--sref", "--sw", "--no", "[CAST]", "[LOCK]"):
            self.assertNotIn(flag, text)
        self.assertIn("16:9", text)

    def test_video_first_then_continue(self):
        cuts = self.spec.cuts(1)
        self.assertTrue(video(self.spec, cuts[0]).startswith("Very slow forward dolly"))
        self.assertTrue(video(self.spec, cuts[1]).startswith("Continue the same move"))
        with self.assertRaises(ValueError):
            video(self.spec, cuts[3])  # 비트의 마지막 컷

    def test_every_block_has_a_distinct_title(self):
        """같은 장면을 전 블록에 돌려쓰다 2블록을 폐기한 적이 있다."""
        titles = [b["title"] for b in self.spec.data["blocks"]]
        self.assertEqual(len(titles), len(set(titles)))

    def test_validation_catches_miscounted_block(self):
        data = Spec.load(SPEC).data
        data["blocks"][0]["beats"] = [["B1", 4], ["B2", 4]]  # 앵커 8 ≠ 헤더 11
        with self.assertRaises(SpecError):
            Spec(data)


if __name__ == "__main__":
    unittest.main()
