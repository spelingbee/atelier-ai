"""
AtelierAI — Remix / feature composition (NEW FILE, additive).

Идея: «собрать новую юбку из 2–3 референсов» — ЭТО НЕ генерация лекала
нейросетью, а КОМПОЗИЦИЯ ПРИЗНАКОВ:
  1) каждое фото -> FeatureVector (силуэт, длина, клёш, годе, разрез, запах...);
  2) пользователь выбирает, что от какого референса взять;
  3) собираем параметрический рецепт -> строим движком.

Честное ограничение: воспроизводятся только те признаки, что есть в библиотеке
шаблонов (5 силуэтов + годе + запах). Декор (бант, фактура) — в инструкции
по пошиву, а не в геометрию.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional

from patterns import Measurements, build_pattern, PATTERN_REGISTRY
from godet import GodetSkirtPattern
from wrap import WrapSkirtPattern

VALID_SILHOUETTES = set(PATTERN_REGISTRY.keys())   # straight/pencil/a_line/half_circle/full_circle


@dataclass
class FeatureVector:
    """Нормализованные признаки одной юбки-референса."""
    silhouette: str = "straight"          # базовый силуэт из 5
    length_cm: float = 60.0
    has_godets: bool = False              # клинья-годе
    n_godets: int = 4
    flare_deg: float = 60.0
    has_slit: bool = False
    has_wrap: bool = False                # запах
    waistband: bool = True
    notes: List[str] = field(default_factory=list)

    def __post_init__(self):
        if self.silhouette not in VALID_SILHOUETTES:
            self.silhouette = "straight"


# подсказка длины из классификатора (mini/knee/midi/maxi)
_LENGTH_CM = {"mini": 40, "knee": 55, "midi": 70, "maxi": 95}


def extract_features(analysis: Dict) -> FeatureVector:
    """Из вывода ai_classifier (или ручного dict) -> FeatureVector."""
    silh = analysis.get("skirt_type", "straight")
    length = analysis.get("length_hint_cm") or _LENGTH_CM.get(
        analysis.get("estimated_length", "knee"), 60)
    notes = []
    if analysis.get("silhouette_notes"):
        notes.append(str(analysis["silhouette_notes"]))
    return FeatureVector(
        silhouette=silh,
        length_cm=float(length),
        has_godets=bool(analysis.get("has_godets", False)),
        n_godets=int(analysis.get("n_godets", 4)),
        flare_deg=float(analysis.get("flare_deg", 60.0)),
        has_slit=bool(analysis.get("has_slit", False)),
        has_wrap=bool(analysis.get("has_wrap", False)),
        waistband=bool(analysis.get("has_waistband", True)),
        notes=notes,
    )


@dataclass
class RemixRecipe:
    silhouette: str
    length_cm: float
    has_godets: bool
    n_godets: int
    flare_deg: float
    has_slit: bool
    has_wrap: bool
    waistband: bool
    provenance: Dict[str, int]            # откуда взят каждый признак (индекс референса)
    notes: List[str]


def remix(features: List[FeatureVector],
          selection: Optional[Dict[str, int]] = None) -> RemixRecipe:
    """Собрать рецепт из 2–3 референсов по ЯВНОМУ выбору пользователя.

    selection: какой референс (индекс) даёт какой признак. Ключи:
        silhouette, length, godets, slit, wrap, waistband
    Если ключ не указан — признак берётся из референса 0 (детерминированно,
    БЕЗ авто-слияния «по ИЛИ»). Обратная совместимость: ключ "details"
    задаёт единый источник сразу для всех деталей.
    """
    if not features:
        raise ValueError("нужен хотя бы один референс")
    sel = selection or {}
    n = len(features)

    def pick(key: str, default: int = 0) -> int:
        idx = sel.get(key, default)
        return idx if isinstance(idx, int) and 0 <= idx < n else default

    det_all = sel.get("details", None)
    det_all = det_all if isinstance(det_all, int) and 0 <= det_all < n else None

    def detail_src(key: str) -> int:
        if key in sel:
            return pick(key, 0)
        if det_all is not None:
            return det_all
        return 0   # детерминированно: из первого референса, без слияния

    si = pick("silhouette", 0)
    li = pick("length", 0)
    gi = detail_src("godets")
    sli = detail_src("slit")
    wi = detail_src("wrap")
    wbi = detail_src("waistband")

    godet_src = features[gi]
    notes = []
    for f in features:
        notes += f.notes
    if features[wi].has_wrap:
        notes.append("Запах/нахлёст и декор (бант) — см. инструкцию по пошиву, не в геометрии лекала.")

    return RemixRecipe(
        silhouette=features[si].silhouette,
        length_cm=features[li].length_cm,
        has_godets=godet_src.has_godets,
        n_godets=godet_src.n_godets,
        flare_deg=godet_src.flare_deg,
        has_slit=features[sli].has_slit,
        has_wrap=features[wi].has_wrap,
        waistband=features[wbi].waistband,
        provenance={"silhouette": si, "length": li, "godets": gi,
                    "slit": sli, "wrap": wi, "waistband": wbi},
        notes=list(dict.fromkeys(notes)),   # уникальные, с сохранением порядка
    )


def build_from_recipe(recipe: RemixRecipe, m: Measurements):
    """Рецепт + мерки -> детали лекала. Длина из рецепта переопределяет мерки.
    Использует новую покомпонентную многослойную сборку (Фаза 3).
    """
    mm = Measurements(
        waist_cm=m.waist_cm, hip_cm=m.hip_cm, length_cm=recipe.length_cm,
        ease_waist=m.ease_waist, ease_hip=m.ease_hip,
        seam_allowance=m.seam_allowance,
    )
    import overlays
    selection = {
        "silhouette": recipe.silhouette,
        "waistband": "band" if recipe.waistband else "facing",
        "closure": "wrap" if recipe.has_wrap else ("slit" if recipe.has_slit else "zip_side"),
        "detail": ["godet"] if recipe.has_godets else [],
    }
    la = overlays.assemble(selection, mm)
    return la.pieces


def sewing_notes(recipe: RemixRecipe) -> List[str]:
    """Короткая инструкция по деталям на основе генератора ТЗ (Фаза 2)."""
    import reconcile
    selection = {
        "silhouette": recipe.silhouette,
        "waistband": "band" if recipe.waistband else "facing",
        "closure": "wrap" if recipe.has_wrap else ("slit" if recipe.has_slit else "zip_side"),
        "detail": ["godet"] if recipe.has_godets else [],
    }
    m = Measurements(waist_cm=72, hip_cm=98, length_cm=recipe.length_cm)
    tz = reconcile.build_tech_spec(selection, m)
    notes = list(tz["construction_order"])
    if tz.get("warnings"):
        notes += [f"Предупреждение: {w}" for w in tz["warnings"]]
    notes += recipe.notes
    return list(dict.fromkeys(notes))
