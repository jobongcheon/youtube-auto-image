"""스펙 → 작업 시트(MD) / 매니페스트(CSV) / 대기열(txt)."""

from __future__ import annotations

import csv
from pathlib import Path

from . import prompts
from .spec import Spec

LIGHT_NAMES = {
    "A": "평면 확산광 (그림자 거의 없음, 짙은 대기 안개)",
    "B": "낮은 겨울 측광 (긴 그림자, 따뜻한 황토 림라이트)",
    "C": "균일 중립광 (무배경, 피사체 단독 — 도해용)",
    "D": "여명 블루아워 (차가운 모노톤, 먼 곳의 약한 온광 하나)",
}


def _header(spec: Spec, mode: str) -> list[str]:
    t = spec.totals
    d = spec.data
    lines = [
        f"# {d['project_title']} — 이미지·영상 프롬프트 시트",
        "",
        f"- 프로젝트: `{d['project']}`",
        f"- 저장 폴더: `{d['output_dir']}`",
        f"- 규모: {t['blocks']}블록 · {t['beats']}비트 · **이미지 {t['images']}장** · **영상 {t['videos']}개**",
        f"- 프롬프트 모드: `{mode}`"
        + ("  (미드저니 문법 — 자리표시자 미치환)" if mode == "mj"
           else "  (나노바나나 프로·Flow용 자연어 — 자리표시자 치환 완료)"),
        f"- 화면비: {d['aspect']} · 1장씩 생성",
        "",
        "## 작업 순서",
        "",
        "1. `1블-b1-k1`을 먼저 한 장 뽑는다.",
        "2. 마음에 드는 결과가 나오면 그 **시드 값을 확보**한다.",
        "3. 이후 모든 프롬프트의 `[SEED]` 자리에 그 값을 넣는다. 이것이 183장의 그림체를 하나로 묶는다.",
        "4. 시트를 위에서 아래로 따라가며 생성 → 바로 위에 적힌 이름으로 저장한다.",
        "5. 중간에 끊기면 `python3 -m src.cli next` 로 이어갈 지점을 찾는다.",
        "",
        "## 조명 코드",
        "",
        "| 코드 | 뜻 | 프롬프트 |",
        "| --- | --- | --- |",
    ]
    for code, text in spec.data["lights"].items():
        lines.append(f"| {code} | {LIGHT_NAMES[code]} | {text} |")
    lines.append("")

    if mode == "mj":
        lines += ["## 공통 블록 (한 번만 세팅)", ""]
        lines += ["### `[CAST]` — 인물 고정", ""]
        for c in spec.data["cast"]:
            lines.append(f"- **{c['name']}** — {c['desc']}")
        lines += ["", f"> {spec.data['cast_note']}", ""]
        for key, label in (("lock", "`[LOCK]` — 스타일 고정"),
                           ("r_paint", "`[R-PAINT]` — 화법"),
                           ("style", "`[STYLE]` — 씬 공통 스타일"),
                           ("forbidden", "`[FORBIDDEN]` — 네거티브")):
            lines += [f"### {label}", "", "```", spec.data[key], "```", ""]
    lines.append("---")
    lines.append("")
    return lines


def sheet(spec: Spec, mode: str = "mj") -> str:
    lines = _header(spec, mode)

    for block in spec.data["blocks"]:
        no = block["no"]
        lines += [
            f"## 제{no}블록 · {block['title']}",
            "",
            f"조명 {block['light']} · {block['seconds']}초 · "
            f"앵커 {block['anchors']} · 클립 {block['clips']}",
            "",
        ]
        for cut in spec.cuts(no):
            if cut.is_first:
                lines += [
                    f"### B{cut.beat_index} {cut.beat_name} "
                    f"({cut.beat_cuts}컷 · {cut.tempo} · {cut.seconds}s)",
                    "",
                ]
            lines += [
                f"**`{cut.stem}{spec.data['image_ext']}`**",
                "",
                "```",
                prompts.image(spec, cut, mode),
                "```",
                "",
            ]
            if not cut.is_last:
                nxt = f"k{cut.cut_index + 1}"
                lines += [
                    f"**`{cut.video_stem}{spec.data['video_ext']}`**  "
                    f"— k{cut.cut_index} → {nxt}",
                    "",
                    "```",
                    prompts.video(spec, cut),
                    "```",
                    "",
                ]
    return "\n".join(lines)


def manifest(spec: Spec, path: Path, mode: str = "mj") -> int:
    """모든 산출물 한 줄씩. 진행 상황 추적과 편집 타임라인 정렬의 기준표."""
    rows = []
    for order, cut in enumerate(spec.cuts(), start=1):
        rows.append({
            "순번": order,
            "종류": "이미지",
            "파일명": cut.stem + spec.data["image_ext"],
            "블록": cut.block_no,
            "블록제목": cut.block_title,
            "비트": f"b{cut.beat_index}",
            "장소": cut.beat_name,
            "컷": f"k{cut.cut_index}/{cut.beat_cuts}",
            "조명": cut.light,
            "초": cut.seconds,
            "프롬프트": prompts.image(spec, cut, mode),
        })
        if not cut.is_last:
            rows.append({
                "순번": order,
                "종류": "영상",
                "파일명": cut.video_stem + spec.data["video_ext"],
                "블록": cut.block_no,
                "블록제목": cut.block_title,
                "비트": f"b{cut.beat_index}",
                "장소": cut.beat_name,
                "컷": f"k{cut.cut_index}→k{cut.cut_index + 1}",
                "조명": cut.light,
                "초": cut.seconds,
                "프롬프트": prompts.video(spec, cut),
            })
    # 엑셀이 UTF-8 CSV를 바로 열도록 BOM을 붙인다.
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def queue(spec: Spec, path: Path, mode: str = "mj") -> int:
    """한 줄에 하나씩: `파일명<TAB>프롬프트`. 붙여넣기 자동화용."""
    lines = [
        f"{c.stem}{spec.data['image_ext']}\t{prompts.image(spec, c, mode)}"
        for c in spec.cuts()
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(lines)
