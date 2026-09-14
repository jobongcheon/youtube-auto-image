"""명령줄 도구.

  build   스펙 → 작업 시트·매니페스트·대기열 생성
  stats   규모 요약
  verify  저장 폴더를 훑어 완료/누락 집계
  next    아직 안 만든 것 중 가장 앞의 프롬프트 출력 (중단 후 이어하기)
  show    특정 파일 하나의 프롬프트만 출력
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import prompts, render
from .spec import Spec, SpecError

DEFAULT_SPEC = Path(__file__).resolve().parent.parent / "spec" / "isunsin.json"
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".webm"}


def _load(args) -> Spec:
    try:
        return Spec.load(args.spec)
    except SpecError as exc:
        sys.exit(f"[스펙 오류] {exc}")


def _planned(spec: Spec, kind: str = "all", mode: str = "natural"):
    """(파일stem, 종류, 프롬프트) 목록을 작업 순서대로.

    이미지를 전부 만든 뒤 Flow에서 영상을 잇는 2단계 작업이라
    kind로 단계를 좁힐 수 있게 한다.
    """
    out = []
    for cut in spec.cuts():
        if kind in ("all", "image"):
            out.append((cut.stem, "이미지", prompts.image(spec, cut, mode)))
        if kind in ("all", "video") and not cut.is_last:
            out.append((cut.video_stem, "영상", prompts.video(spec, cut)))
    return out


def _present(folder: Path) -> set[str]:
    """폴더에 실제로 있는 파일의 확장자 뗀 이름. 확장자는 따지지 않는다."""
    if not folder.is_dir():
        return set()
    keep = IMAGE_SUFFIXES | VIDEO_SUFFIXES
    return {p.stem for p in folder.iterdir()
            if p.is_file() and p.suffix.lower() in keep}


# ---------------------------------------------------------------- 명령

def cmd_build(args) -> None:
    spec = _load(args)
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    made = []
    for mode, name in (("mj", "프롬프트시트_미드저니.md"),
                       ("natural", "프롬프트시트_나노바나나.md")):
        if args.mode not in (mode, "both"):
            continue
        path = outdir / name
        path.write_text(render.sheet(spec, mode), encoding="utf-8")
        made.append((path, f"{mode} 시트"))

    mode = "natural" if args.mode == "natural" else "mj"
    n = render.manifest(spec, outdir / "매니페스트.csv", mode)
    made.append((outdir / "매니페스트.csv", f"{n}행"))
    n = render.queue(spec, outdir / "대기열_이미지.tsv", mode)
    made.append((outdir / "대기열_이미지.tsv", f"{n}행"))
    n = render.webapp(spec, outdir / "작업대.html")
    made.append((outdir / "작업대.html", f"{n // 1024}KB"))

    for path, note in made:
        print(f"  생성  {path}  ({note})")
    t = spec.totals
    print(f"\n총 {t['blocks']}블록 · 이미지 {t['images']}장 · 영상 {t['videos']}개")


def cmd_stats(args) -> None:
    spec = _load(args)
    t = spec.totals
    print(f"{spec.data['project_title']}\n")
    print(f"{'블록':>4} {'조명':>4} {'비트':>4} {'이미지':>6} {'영상':>5}  제목")
    for block in spec.data["blocks"]:
        print(f"{block['no']:>4} {block['light']:>4} {len(block['beats']):>4} "
              f"{block['anchors']:>6} {block['clips']:>5}  {block['title']}")
    print(f"\n{'합계':>4} {'':>4} {t['beats']:>4} {t['images']:>6} {t['videos']:>5}")


def cmd_verify(args) -> None:
    spec = _load(args)
    folder = Path(args.dir or spec.data["output_dir"])
    have = _present(folder)
    if not folder.is_dir():
        sys.exit(f"[없음] 폴더를 찾을 수 없다: {folder}")

    planned = _planned(spec, args.kind)
    missing = [(s, k) for s, k, _ in planned if s not in have]
    done = len(planned) - len(missing)
    print(f"폴더: {folder}")
    print(f"완료 {done} / {len(planned)}  (누락 {len(missing)})\n")

    for block in spec.data["blocks"]:
        pre = f"{block['no']}블-"
        tot = [s for s, _, _ in planned if s.startswith(pre)]
        miss = [s for s, _ in missing if s.startswith(pre)]
        mark = "완료" if not miss else f"누락 {len(miss)}"
        print(f"  {block['no']:>2}블록  {len(tot) - len(miss):>3}/{len(tot):<3}  {mark}")

    extra = sorted(have - {s for s, _, _ in _planned(spec, "all")})
    if extra:
        print(f"\n계획에 없는 파일 {len(extra)}개: {', '.join(extra[:8])}"
              + (" …" if len(extra) > 8 else ""))


def cmd_next(args) -> None:
    spec = _load(args)
    folder = Path(args.dir or spec.data["output_dir"])
    have = _present(folder)
    remaining = [(s, k, p) for s, k, p in _planned(spec, args.kind, args.mode)
                 if s not in have]
    if not remaining:
        t = spec.totals
        if args.kind == "image":
            left = [x for x, _, _ in _planned(spec, "video") if x not in have]
            print(f"이미지 {t['images']}장 완료.")
            print(f"다음 단계: Flow Omni에서 영상 {len(left)}개."
                  if left else f"영상 {t['videos']}개도 완료. 전부 끝났다.")
        elif args.kind == "video":
            print(f"영상 {t['videos']}개 완료.")
        else:
            print(f"전부 완료. 이미지 {t['images']}장 · 영상 {t['videos']}개.")
        return
    print(f"남은 작업 {len(remaining)}개. 다음 {min(args.count, len(remaining))}개:\n")
    for stem, kind, prompt in remaining[:args.count]:
        ext = spec.data["image_ext"] if kind == "이미지" else spec.data["video_ext"]
        print(f"── {stem}{ext}  [{kind}]")
        print(prompt)
        print()


def cmd_show(args) -> None:
    spec = _load(args)
    for stem, kind, prompt in _planned(spec, "all", args.mode):
        if stem == args.name:
            print(f"[{kind}] {stem}\n{prompt}")
            return
    sys.exit(f"[없음] 계획에 없는 이름: {args.name}")


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(prog="youtube-auto-image", description=__doc__)
    parser.add_argument("--spec", default=str(DEFAULT_SPEC), help="스펙 JSON 경로")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("build", help="시트·매니페스트·대기열 생성")
    p.add_argument("--out", default="out")
    p.add_argument("--mode", choices=["mj", "natural", "both"], default="both")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("stats", help="규모 요약")
    p.set_defaults(func=cmd_stats)

    p = sub.add_parser("verify", help="저장 폴더 대조")
    p.add_argument("--dir", help="기본값은 스펙의 output_dir")
    p.add_argument("--kind", choices=["image", "video", "all"], default="all",
                   help="image=이미지 단계만, video=영상 단계만")
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("next", help="이어서 만들 프롬프트 출력")
    p.add_argument("--dir")
    p.add_argument("-n", "--count", type=int, default=1)
    p.add_argument("--kind", choices=["image", "video", "all"], default="image",
                   help="기본은 image — 이미지 183장을 먼저 끝낸다")
    p.add_argument("--mode", choices=["mj", "natural"], default="natural")
    p.set_defaults(func=cmd_next)

    p = sub.add_parser("show", help="이름 하나의 프롬프트")
    p.add_argument("name", help="예: 2블-b1-k3")
    p.add_argument("--mode", choices=["mj", "natural"], default="natural")
    p.set_defaults(func=cmd_show)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        # head 등으로 출력을 잘라 쓸 때 나는 정상적인 종료다.
        sys.stderr.close()
