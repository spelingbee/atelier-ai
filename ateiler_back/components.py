"""
AtelierAI — ПОКОМПОНЕНТНЫЙ КАРКАС (Фаза 1, NEW FILE, аддитивно).

Ядро (patterns.py / export.py) НЕ РЕДАКТИРУЕТСЯ. Здесь вводится новый слой
поверх существующих 13 типов юбок: изделие описывается как набор ВЗАИМО-
ЗАМЕНЯЕМЫХ ЧАСТЕЙ в СЛОТАХ, у каждой части есть КОНТРАКТ СТЫКОВ (edges),
правила СОВМЕСТИМОСТИ и шаги пошива. Решатель собирает выбор пользователя в
целостную сборку, проверяет совместимость, подставляет дефолты и считает
согласование талиевого стыка (сборка vs пояс).

Это Фаза 1 ТЗ: слоты + реестр компонентов + контракт стыков + решатель.
Полный решатель стыков (вытачки/прибавки) и генератор ТЗ — Фаза 2.

Все длины в сантиметрах.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

import patterns as P
from patterns import Measurements, PatternPiece, build_pattern, StraightSkirtPattern

# импорт авто-регистрирует расширенные типы в PATTERN_REGISTRY
import skirt_types_extra  # noqa: F401  (pleated, tiered, yoke)
import skirt_types_more   # noqa: F401  (tulip, mermaid, hi_low, bubble, skort)
import pockets            # noqa: F401  (карманы: inseam/patch/cargo/welt)


# --------------------------------------------------------------------------- #
#  Слоты
# --------------------------------------------------------------------------- #
SLOT_WAISTBAND = "waistband"   # талия / пояс
SLOT_SILHOUETTE = "silhouette"  # базовый силуэт (несущий слой)
SLOT_HEM = "hem"               # обработка низа
SLOT_CLOSURE = "closure"       # застёжка
SLOT_OVERLAY = "overlay"       # верхний крой поверх базы
SLOT_DETAIL = "detail"         # локальные детали (мультивыбор)

# порядок вдоль оси тела / порядок сборки
SLOT_ORDER = [SLOT_WAISTBAND, SLOT_SILHOUETTE, SLOT_HEM, SLOT_CLOSURE,
              SLOT_OVERLAY, SLOT_DETAIL]


# --------------------------------------------------------------------------- #
#  Контракт стыков и результат сборки части
# --------------------------------------------------------------------------- #
@dataclass
class Edge:
    """Край соединения части. length_cm — ФАКТИЧЕСКАЯ длина среза."""
    name: str            # "waist" | "hip" | "hem" | "top" | "side"
    length_cm: float
    easeable: bool = True   # можно ли присборить/припосадить этот срез
    note: str = ""


@dataclass
class ComponentResult:
    slot: str
    key: str
    title: str
    pieces: List[PatternPiece] = field(default_factory=list)
    edges: Dict[str, Edge] = field(default_factory=dict)
    sewing_steps: List[str] = field(default_factory=list)
    geometry_ready: bool = True   # False => часть пока только в ТЗ, не в геометрии


# --------------------------------------------------------------------------- #
#  Геометрические измерители (честно меряем по построенным деталям)
# --------------------------------------------------------------------------- #
def _flat_top_width(piece: PatternPiece, tol: float = 0.6) -> float:
    """Плоская ширина ВЕРХНЕГО среза детали (для прямоугольных/трапеция)."""
    ys = [y for _, y in piece.points]
    ymin = min(ys)
    tops = [x for x, y in piece.points if y <= ymin + tol]
    return (max(tops) - min(tops)) if len(tops) >= 2 else 0.0


# Классификация силуэтов по поведению ТАЛИЕВОГО среза
_WAIST_FITTED_DARTS = {"straight", "pencil", "a_line", "tulip", "mermaid"}
_WAIST_CONICAL = {"half_circle", "full_circle", "hi_low"}
_WAIST_RADIAL_GATHERED = {"hi_low_gathered"}
_WAIST_FITTED_YOKE = {"yoke"}
_WAIST_GATHERED = {"tiered", "bubble"}   # меряем по геометрии
_WAIST_PLEATED = {"pleated"}
_WAIST_SKORT = {"skort"}


def silhouette_waist_edge(silh: str, pieces: List[PatternPiece],
                          m: Measurements) -> Edge:
    """Фактическая длина талиевого среза силуэта + как он формуется.

    Возвращает Edge(length_cm = ПЛОСКАЯ длина среза до сборки на пояс).
    Для вытачных/конических силуэтов плоский = готовому = waist_eff.
    Для сборочных силуэтов плоский > waist_eff (разница уходит в сборку).
    """
    waist_eff = m.waist_cm + m.ease_waist
    if silh in _WAIST_RADIAL_GATHERED:
        cls = P.PATTERN_REGISTRY.get(silh)
        g = float(getattr(cls, "gather", 1.6))
        return Edge("waist", round(waist_eff * g, 1), easeable=True,
                    note=f"радиальный крой со сборкой ×{g:g}")
    if silh in _WAIST_PLEATED:
        full = getattr(P.PATTERN_REGISTRY.get("pleated"), "fullness", 3.0)
        return Edge("waist", waist_eff * full, easeable=True,
                    note=f"плиссе ×{full:g} (закладывается в складки)")
    if silh in _WAIST_GATHERED:
        # меряем плоский верх по самой широкой верхней детали
        cand = [p for p in pieces if p.name != "waistband"]
        flat = 0.0
        for p in cand:
            w = _flat_top_width(p) * (2 if p.cut_on_fold else 1) * max(1, p.quantity)
            flat = max(flat, w)
        flat = flat or waist_eff
        return Edge("waist", flat, easeable=True, note="сборка по талии")
    # вытачные / конические / кокетка / юбка-шорты => готовый срез = waist_eff
    note = {
        "conical": "конический крой (срез = талии)",
    }.get("conical" if silh in _WAIST_CONICAL else "", "")
    if silh in _WAIST_CONICAL:
        note = "конический крой (срез = талии)"
    elif silh in _WAIST_FITTED_DARTS:
        note = "вытачки убирают раствор (срез = талии)"
    elif silh in _WAIST_FITTED_YOKE:
        note = "облегающая кокетка (срез = талии)"
    elif silh in _WAIST_SKORT:
        note = "юбка-шорты (срез = талии)"
    return Edge("waist", waist_eff, easeable=False, note=note)


# --------------------------------------------------------------------------- #
#  Реестр компонентов
# --------------------------------------------------------------------------- #
@dataclass
class ComponentSpec:
    key: str
    slot: str
    title: str
    # требования/конфликты по тегам силуэта
    requires_silhouette: Optional[set] = None   # допустимые силуэты
    conflicts_silhouette: Optional[set] = None
    recommends: Optional[List[str]] = None       # ключи, которые стоит включить
    geometry_ready: bool = True
    note: str = ""


# --- Силуэты (несущий слой): выносим существующие 13 типов в части --------- #
SILHOUETTE_TITLES = {
    "hi_low_gathered": "Асимметрия (сборка)",
    "straight": "Прямая", "pencil": "Карандаш", "a_line": "А-силуэт",
    "half_circle": "Полусолнце", "full_circle": "Солнце",
    "tulip": "Тюльпан", "mermaid": "Русалка/годе", "hi_low": "Асимметрия",
    "bubble": "Баллон", "skort": "Юбка-шорты",
    "pleated": "Плиссе", "tiered": "Ярусная", "yoke": "Кокетка+сборка",
}

# --- Пояса --------------------------------------------------------------- #
WAISTBAND_SPECS = {
    "band": ComponentSpec("band", SLOT_WAISTBAND, "Притачной пояс",
                          note="жёсткий пояс по обхвату талии"),
    "elastic": ComponentSpec("elastic", SLOT_WAISTBAND, "Кулиса/резинка",
                             note="приминает любую сборку"),
    "facing": ComponentSpec("facing", SLOT_WAISTBAND, "Обтачка",
                            note="внутренняя обтачка без пояса"),
}

# --- Застёжки ------------------------------------------------------------ #
CLOSURE_SPECS = {
    "zip_side": ComponentSpec("zip_side", SLOT_CLOSURE, "Молния сбоку"),
    "zip_back": ComponentSpec("zip_back", SLOT_CLOSURE, "Молния сзади"),
    "slit": ComponentSpec("slit", SLOT_CLOSURE, "Шлица/разрез"),
    "wrap": ComponentSpec("wrap", SLOT_CLOSURE, "Запах"),
    "none": ComponentSpec("none", SLOT_CLOSURE, "Без застёжки (резинка)"),
}

# --- Детали (мультивыбор) ------------------------------------------------ #
DETAIL_SPECS = {
    "godet": ComponentSpec("godet", SLOT_DETAIL, "Клинья-годе",
                           requires_silhouette={"straight", "pencil", "a_line", "mermaid"},
                           conflicts_silhouette={"full_circle", "half_circle", "pleated", "tiered"},
                           note="требует облегающий силуэт"),
    "pockets": ComponentSpec("pockets", SLOT_DETAIL, "Карманы", geometry_ready=True,
                             note="подтип: inseam/patch/cargo/welt (по умолч. inseam)"),
    "slit_detail": ComponentSpec("slit_detail", SLOT_DETAIL, "Разрез", geometry_ready=False),
    "pleats_detail": ComponentSpec("pleats_detail", SLOT_DETAIL, "Складки", geometry_ready=False),
}

# --- Оверлеи (верхний крой; геометрия — Фаза 3) -------------------------- #
OVERLAY_SPECS = {
    "none": ComponentSpec("none", SLOT_OVERLAY, "Без оверлея"),
    "flap": ComponentSpec("flap", SLOT_OVERLAY, "Флап-запах", geometry_ready=False),
    "peplum": ComponentSpec("peplum", SLOT_OVERLAY, "Баска", geometry_ready=False),
    "yoke_overlay": ComponentSpec("yoke_overlay", SLOT_OVERLAY, "Кокетка-оверлей", geometry_ready=False),
    "bow": ComponentSpec("bow", SLOT_OVERLAY, "Драпировка/бант", geometry_ready=False),
}

# --- Низ (Фаза 2/3 — пока маркер в ТЗ) ----------------------------------- #
HEM_SPECS = {
    "straight": ComponentSpec("straight", SLOT_HEM, "Ровный низ"),
    "hi_low": ComponentSpec("hi_low", SLOT_HEM, "Асимметрия (hi-low)", geometry_ready=False),
    "ruffle": ComponentSpec("ruffle", SLOT_HEM, "Волан", geometry_ready=False),
}


def slot_catalog() -> Dict[str, List[Dict]]:
    """Что можно выбрать в каждом слоте (для UI/ИИ)."""
    return {
        SLOT_SILHOUETTE: [{"key": k, "title": v} for k, v in SILHOUETTE_TITLES.items()],
        SLOT_WAISTBAND: [{"key": s.key, "title": s.title} for s in WAISTBAND_SPECS.values()],
        SLOT_CLOSURE: [{"key": s.key, "title": s.title} for s in CLOSURE_SPECS.values()],
        SLOT_DETAIL: [{"key": s.key, "title": s.title} for s in DETAIL_SPECS.values()],
        SLOT_OVERLAY: [{"key": s.key, "title": s.title} for s in OVERLAY_SPECS.values()],
        SLOT_HEM: [{"key": s.key, "title": s.title} for s in HEM_SPECS.values()],
    }


# --------------------------------------------------------------------------- #
#  Сборка пояса
# --------------------------------------------------------------------------- #
def build_waistband(key: str, m: Measurements) -> ComponentResult:
    waist_eff = m.waist_cm + m.ease_waist
    hip_eff = m.hip_cm + m.ease_hip
    spec = WAISTBAND_SPECS.get(key, WAISTBAND_SPECS["band"])
    if key == "elastic":
        # кулиса должна пройти через бёдра; резинка стянет до талии
        w = hip_eff + 4.0
        h = 7.0
        pts = [(0, 0), (0, h), (w, h), (w, 0), (0, 0)]
        piece = PatternPiece(name="waistband", points=pts,
                             grain_line=((w * 0.25, h / 2), (w * 0.75, h / 2)),
                             labels=[{"text": "КУЛИСА/РЕЗИНКА × 1", "x": w / 2, "y": h / 2,
                                      "size": 1.0, "bold": True}],
                             notches=[(w / 2, 0)], quantity=1)
        edge = Edge("waist", waist_eff, easeable=True, note="резинка стягивает до талии")
        steps = ["Подогнуть кулису, вставить резинку по обхвату талии."]
        return ComponentResult(SLOT_WAISTBAND, key, spec.title, [piece], {"waist": edge}, steps)
    if key == "facing":
        w = waist_eff + 3.0
        h = 4.0
        pts = [(0, 0), (0, h), (w, h), (w, 0), (0, 0)]
        piece = PatternPiece(name="waistband", points=pts,
                             grain_line=((w * 0.25, h / 2), (w * 0.75, h / 2)),
                             labels=[{"text": "ОБТАЧКА × 1", "x": w / 2, "y": h / 2,
                                      "size": 1.0, "bold": True}],
                             notches=[(w / 2, 0)], quantity=1)
        edge = Edge("waist", waist_eff, easeable=False, note="обтачка по талии")
        steps = ["Притачать обтачку по верхнему срезу, отвернуть внутрь."]
        return ComponentResult(SLOT_WAISTBAND, key, spec.title, [piece], {"waist": edge}, steps)
    # band (по умолчанию)
    piece = StraightSkirtPattern(m).waistband()
    edge = Edge("waist", waist_eff, easeable=False, note="притачной пояс по талии")
    steps = ["Притачать пояс по верхнему срезу; застёжка по выбору."]
    return ComponentResult(SLOT_WAISTBAND, "band", WAISTBAND_SPECS["band"].title,
                           [piece], {"waist": edge}, steps)


# --------------------------------------------------------------------------- #
#  Решатель: собрать выбор в целостную сборку
# --------------------------------------------------------------------------- #
@dataclass
class Assembly:
    measurements: Measurements
    selection: Dict[str, object]
    pieces: List[PatternPiece]
    components: Dict[str, ComponentResult]
    waist_join: Dict[str, object]
    warnings: List[str]
    sewing_spec: List[str]


DEFAULTS = {
    SLOT_SILHOUETTE: "straight",
    SLOT_WAISTBAND: "band",
    SLOT_CLOSURE: "zip_side",
    SLOT_OVERLAY: "none",
    SLOT_HEM: "straight",
    SLOT_DETAIL: [],
}


def resolve(selection: Dict[str, object], m: Measurements) -> Assembly:
    """Главная функция Фазы 1: собрать выбор пользователя в сборку.

    selection: {silhouette, waistband, closure, overlay, hem, details:[...]}.
    Любой пропущенный слот берёт дефолт. Проверяется совместимость, талиевый
    стык согласуется (сборка vs пояс), формируется черновое ТЗ.
    """
    sel = dict(DEFAULTS)
    sel.update(selection or {})
    warnings: List[str] = []

    silh = sel[SLOT_SILHOUETTE]
    if silh not in SILHOUETTE_TITLES:
        warnings.append(f"Силуэт '{silh}' неизвестен → взят 'straight'.")
        silh = sel[SLOT_SILHOUETTE] = "straight"

    # --- 1. Несущий слой: строим силуэт через движок, убираем его пояс ----- #
    raw = build_pattern(silh, m)
    silh_pieces = [p for p in raw if p.name != "waistband"]
    waist_edge = silhouette_waist_edge(silh, silh_pieces, m)
    components: Dict[str, ComponentResult] = {
        SLOT_SILHOUETTE: ComponentResult(
            SLOT_SILHOUETTE, silh, SILHOUETTE_TITLES[silh], silh_pieces,
            {"waist": waist_edge}, [f"Стачать детали силуэта «{SILHOUETTE_TITLES[silh]}»."]),
    }

    # --- 2. Пояс ----------------------------------------------------------- #
    wb = build_waistband(sel[SLOT_WAISTBAND], m)
    components[SLOT_WAISTBAND] = wb

    # --- 3. Согласование талиевого стыка ----------------------------------- #
    waist_eff = m.waist_cm + m.ease_waist
    skirt_waist = waist_edge.length_cm
    band_easeable = wb.edges["waist"].easeable
    ratio = skirt_waist / waist_eff if waist_eff else 1.0
    join_method = "1:1 (срез = поясу)"
    if ratio > 1.08:
        if band_easeable:
            join_method = f"сборка ×{ratio:.2f} под резинку"
        else:
            join_method = f"присборить срез {skirt_waist:.0f} см в пояс {waist_eff:.0f} см (×{ratio:.2f})"
            if sel[SLOT_WAISTBAND] == "band" and ratio > 1.3:
                warnings.append(
                    f"Талиевый срез ×{ratio:.2f} от пояса: для притачного пояса нужна сильная "
                    f"сборка. Лучше выбрать кулису/резинку.")
    waist_join = {
        "skirt_waist_cm": round(skirt_waist, 1),
        "waistband_cm": round(waist_eff, 1),
        "ratio": round(ratio, 2),
        "method": join_method,
        "construction": waist_edge.note,
    }

    # --- 4. Застёжка ------------------------------------------------------- #
    closure = sel[SLOT_CLOSURE]
    if closure not in CLOSURE_SPECS:
        warnings.append(f"Застёжка '{closure}' неизвестна → 'zip_side'.")
        closure = sel[SLOT_CLOSURE] = "zip_side"
    if silh == "pencil" and closure not in ("slit", "zip_back"):
        warnings.append("Карандаш требует шлицу для шага — добавьте 'slit' или молнию сзади.")
    if sel[SLOT_WAISTBAND] == "elastic" and closure not in ("none", "wrap"):
        warnings.append("С резинкой застёжка обычно не нужна → 'none'.")
    components[SLOT_CLOSURE] = ComponentResult(
        SLOT_CLOSURE, closure, CLOSURE_SPECS[closure].title, [],
        {}, [f"Застёжка: {CLOSURE_SPECS[closure].title}."])

    # --- 5. Детали (мультивыбор) ------------------------------------------ #
    details = sel.get(SLOT_DETAIL) or sel.get("details") or []
    if isinstance(details, str):
        details = [details]
    # подтип кармана можно задать как "pockets:<kind>" или selection["pocket_type"]
    default_pocket = sel.get("pocket_type") or "inseam"
    kept_details = []
    detail_steps: List[str] = []
    detail_pieces: List[PatternPiece] = []
    for raw_d in details:
        d = raw_d
        pocket_kind = None
        if isinstance(raw_d, str) and ":" in raw_d:
            base, _, sub = raw_d.partition(":")
            d = base
            if base == "pockets":
                pocket_kind = sub or default_pocket
        spec = DETAIL_SPECS.get(d)
        if not spec:
            warnings.append(f"Деталь '{raw_d}' неизвестна → пропущена.")
            continue
        if spec.conflicts_silhouette and silh in spec.conflicts_silhouette:
            warnings.append(f"Деталь «{spec.title}» несовместима с силуэтом «{SILHOUETTE_TITLES[silh]}» → пропущена.")
            continue
        if spec.requires_silhouette and silh not in spec.requires_silhouette:
            warnings.append(f"Деталь «{spec.title}» требует облегающий силуэт → пропущена.")
            continue
        kept_details.append(d)
        if d == "pockets":
            kind = pocket_kind or default_pocket
            if kind not in pockets.POCKET_REGISTRY:
                warnings.append(f"Тип кармана '{kind}' неизвестен → '{default_pocket}'.")
                kind = default_pocket if default_pocket in pockets.POCKET_REGISTRY else "inseam"
            pres = pockets.build_pocket(kind, m)
            detail_pieces.extend(pres.pieces)
            detail_steps.append(f"Карманы — {pres.title} ({pres.placement}):")
            detail_steps.extend(f"  • {s}" for s in pres.sewing_steps)
        elif not spec.geometry_ready:
            warnings.append(f"Деталь «{spec.title}» пока вносится только в ТЗ (геометрия — позже).")
            detail_steps.append(f"Деталь: {spec.title}.")
        else:
            detail_steps.append(f"Деталь: {spec.title}.")
    components[SLOT_DETAIL] = ComponentResult(
        SLOT_DETAIL, ",".join(kept_details) or "none", "Детали", detail_pieces, {},
        detail_steps)

    # --- 6. Оверлей -------------------------------------------------------- #
    overlay = sel.get(SLOT_OVERLAY, "none")
    if overlay not in OVERLAY_SPECS:
        warnings.append(f"Оверлей '{overlay}' неизвестен → 'none'.")
        overlay = "none"
    ov_spec = OVERLAY_SPECS[overlay]
    if overlay != "none" and not ov_spec.geometry_ready:
        warnings.append(f"Оверлей «{ov_spec.title}» пока вносится только в ТЗ (геометрия — Фаза 3).")
    components[SLOT_OVERLAY] = ComponentResult(
        SLOT_OVERLAY, overlay, ov_spec.title, [], {},
        ([f"Верхний крой: {ov_spec.title} — настрочить поверх базы."] if overlay != "none" else []),
        geometry_ready=ov_spec.geometry_ready)

    # --- 7. Собрать детали лекала (только готовая геометрия) --------------- #
    pieces: List[PatternPiece] = list(silh_pieces) + list(wb.pieces) + list(detail_pieces)

    # --- 8. Черновое ТЗ на пошив ------------------------------------------ #
    spec_lines: List[str] = []
    spec_lines.append(f"Силуэт: {SILHOUETTE_TITLES[silh]}; пояс: {wb.title}; застёжка: {CLOSURE_SPECS[closure].title}.")
    spec_lines.append(f"Талиевый стык: {waist_join['method']} ({waist_join['construction']}).")
    spec_lines.extend(components[SLOT_DETAIL].sewing_steps)
    if overlay != "none":
        spec_lines.append(f"Оверлей: {ov_spec.title} (настрочить поверх базы).")
    spec_lines.append("Детали кроя: " + "; ".join(
        f"{p.name}×{p.quantity}{' по сгибу' if p.cut_on_fold else ''}" for p in pieces))

    return Assembly(
        measurements=m, selection=sel, pieces=pieces, components=components,
        waist_join=waist_join, warnings=warnings, sewing_spec=spec_lines)
