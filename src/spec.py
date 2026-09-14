"""스펙 파일(JSON)을 읽어 검증하고, 컷 단위로 펼쳐주는 모듈."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Cut:
    """이미지 한 장(앵커 K) 또는 그 뒤에 이어지는 영상 한 개(클립 V)의 좌표."""

    block_no: int
    block_title: str
    light: str
    tempo: str
    beat_code: str          # B1~B5
    beat_index: int         # 1부터
    beat_name: str
    beat_cuts: int          # 이 비트의 총 컷 수
    cut_index: int          # 1부터
    seconds: int            # 이 비트에 배정된 길이(초)

    @property
    def stem(self) -> str:
        return f"{self.block_no}블-b{self.beat_index}-k{self.cut_index}"

    @property
    def video_stem(self) -> str:
        return f"{self.block_no}블-b{self.beat_index}-v{self.cut_index}"

    @property
    def is_first(self) -> bool:
        return self.cut_index == 1

    @property
    def is_last(self) -> bool:
        return self.cut_index == self.beat_cuts


class SpecError(ValueError):
    pass


class Spec:
    def __init__(self, data: dict):
        self.data = data
        self._validate()

    # ---------- 로드 ----------

    @classmethod
    def load(cls, path: str | Path) -> "Spec":
        with open(path, encoding="utf-8") as fh:
            return cls(json.load(fh))

    # ---------- 검증 ----------

    def _validate(self) -> None:
        """헤더의 앵커/클립 수와 비트 구성이 어긋나면 즉시 실패시킨다.

        블록 내용과 프롬프트가 어긋난 채로 수백 장을 생성하는 사고를 막는 방어선이다.
        비트 하나는 컷 N개와 그 사이를 잇는 영상 N-1개를 만들므로
        (앵커 합) - (비트 수) == (클립 합) 이 항상 성립해야 한다.
        """
        errors: list[str] = []
        seen: set[int] = set()

        for block in self.data["blocks"]:
            no = block["no"]
            if no in seen:
                errors.append(f"{no}블록: 번호 중복")
            seen.add(no)

            if block["light"] not in self.data["lights"]:
                errors.append(f"{no}블록: 알 수 없는 조명 코드 {block['light']!r}")

            cuts = [n for _, n in block["beats"]]
            for code, n in block["beats"]:
                if code not in self.data["scenes"]:
                    errors.append(f"{no}블록: 알 수 없는 장소 코드 {code!r}")
                if n < 2:
                    errors.append(f"{no}블록 {code}: 컷이 {n}개 — 최소 2개여야 영상을 이을 수 있다")

            anchors, clips = sum(cuts), sum(cuts) - len(cuts)
            if anchors != block["anchors"]:
                errors.append(f"{no}블록: 앵커 합 {anchors} ≠ 헤더 {block['anchors']}")
            if clips != block["clips"]:
                errors.append(f"{no}블록: 클립 합 {clips} ≠ 헤더 {block['clips']}")

        if errors:
            raise SpecError("스펙 검증 실패:\n  - " + "\n  - ".join(errors))

    # ---------- 조회 ----------

    def scene(self, code: str) -> dict:
        return self.data["scenes"][code]

    def light(self, code: str) -> str:
        return self.data["lights"][code]

    def cuts(self, block_no: int | None = None) -> list[Cut]:
        """모든 컷을 블록 → 비트 → 컷 순서로 펼친다."""
        out: list[Cut] = []
        for block in self.data["blocks"]:
            if block_no is not None and block["no"] != block_no:
                continue
            per_beat = round(block["seconds"] / len(block["beats"]))
            for beat_index, (code, n) in enumerate(block["beats"], start=1):
                for cut_index in range(1, n + 1):
                    out.append(
                        Cut(
                            block_no=block["no"],
                            block_title=block["title"],
                            light=block["light"],
                            tempo=block["tempo"],
                            beat_code=code,
                            beat_index=beat_index,
                            beat_name=self.scene(code)["name"],
                            beat_cuts=n,
                            cut_index=cut_index,
                            seconds=per_beat,
                        )
                    )
        return out

    @property
    def totals(self) -> dict[str, int]:
        cuts = self.cuts()
        beats = sum(len(b["beats"]) for b in self.data["blocks"])
        return {
            "blocks": len(self.data["blocks"]),
            "beats": beats,
            "images": len(cuts),
            "videos": len(cuts) - beats,
        }
