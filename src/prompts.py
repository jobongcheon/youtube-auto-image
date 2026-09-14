"""컷 좌표 → 실제 프롬프트 문자열.

두 가지 모드를 낸다.

mj       원본 스펙과 글자 단위로 동일한 미드저니 문법. [CAST] 같은 자리표시자를
         그대로 두고 --ar / --sref / --sw / --no 플래그를 붙인다.
natural  나노바나나 프로·Flow용. 자리표시자를 실제 문장으로 펼치고 플래그를
         평범한 영어로 바꾼다. 이 엔진들은 미드저니 플래그를 이해하지 못한다.
"""

from __future__ import annotations

from .spec import Cut, Spec

SEED = "[SEED]"


def _framing(cut: Cut) -> str:
    """이 컷이 비트 안에서 어느 위치인지 알려주는 도입 문구."""
    if cut.is_first:
        return None  # 첫 컷은 장면 설명 자체로 시작한다
    if cut.is_last:
        return "the same scene from the same camera height, closest framing of this beat"
    return (
        "the same scene from the same camera height, "
        f"progressively closer ({cut.cut_index} of {cut.beat_cuts})"
    )


# ---------------------------------------------------------------- 미드저니

def image_mj(spec: Spec, cut: Cut) -> str:
    scene = spec.scene(cut.beat_code)
    head = _framing(cut) or scene["desc"]
    props = ", ".join(p["ko"] for p in spec.data["props"])
    return (
        f"{head}, {scene['shot']}, {spec.light(cut.light)}, "
        f"{spec.data['era']['ko']}, {props}, "
        f"[CAST], [LOCK] , [R-PAINT] , [STYLE] "
        f"--ar {spec.data['aspect']} --sref {SEED} --sw {spec.data['sref_weight']} "
        f"--no [FORBIDDEN]"
    )


# ---------------------------------------------------------------- 자연어

def image_natural(spec: Spec, cut: Cut) -> str:
    scene = spec.scene(cut.beat_code)
    head = _framing(cut) or scene["desc"]
    props = ", ".join(p["en"] for p in spec.data["props"])
    cast = "; ".join(f"{c['desc']}" for c in spec.data["cast"])
    return (
        f"{head}, {scene['shot']}, {spec.light(cut.light)}. "
        f"Setting: {spec.data['era']['en']}. "
        f"Recurring props that must appear consistently: {props}. "
        f"Characters (keep identical across every image): {cast}. "
        f"{spec.data['cast_note_en']} "
        f"{spec.data['lock']} "
        f"{spec.data['r_paint']} "
        f"{spec.data['style']} "
        f"Render in a {spec.data['aspect']} landscape frame. "
        f"Do not include: {spec.data['forbidden']}."
    )


def image(spec: Spec, cut: Cut, mode: str = "mj") -> str:
    return image_mj(spec, cut) if mode == "mj" else image_natural(spec, cut)


# ---------------------------------------------------------------- 영상(V)

def video(spec: Spec, cut: Cut) -> str:
    """cut → 다음 컷으로 이어지는 클립의 프롬프트. 마지막 컷에는 클립이 없다."""
    if cut.is_last:
        raise ValueError(f"{cut.stem}은 비트의 마지막 컷이라 이어붙일 영상이 없다")
    move = (
        spec.scene(cut.beat_code)["move"]
        if cut.is_first
        else spec.data["video_continue"]
    )
    return f"{move} {spec.data['video_tail']}"
