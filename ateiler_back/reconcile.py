"""
AtelierAI — РЕШАТЕЛЬ СТЫКОВ + ГЕНЕРАТОР ТЗ (Фаза 2, NEW FILE, аддитивно).

Ядро (patterns.py / export.py) и Фаза 1 (components.py) НЕ РЕДАКТИРУЮТСЯ.
Здесь поверх Assembly из components.resolve() добавляется:
  1. ПОЛНЫЙ РЕШАТЕЛЬ ТАЛИЕВОГО СТЫКА — раствор (hip-waist) распределяется на
     вытачки + боковые швы (вытачные силуэты), либо в сборку (сборочные), либо
     в складки (плиссе), либо 1:1 (конический). Считаем числа, а не текст.
  2. СТРУКТУРНЫЙ ГЕНЕРАТОР ТЗ — dict с секциями (модель, мерки, материалы,
     детали кроя, согласование талии, припуски, порядок пошива) + рендер в md.
  3. verify_assembly() — проверка СШИВАЕМОСТИ собранного из частей лекала
     (геометрия, припуск, экспорт, сходимость талиевого стыка, надевание).

Все длины в сантиметрах.
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from typing import List, Dict, Optional

import patterns as P
from patterns import Measurements, PatternPiece
import components as C
import export


# --------------------------------------------------------------------------- #
#  Решатель талиевого стыка
# --------------------------------------------------------------------------- #
@dataclass
class Dart:
    location: str        # "перед" | "спинка"
    count: int           # сколько таких вытачек всего на изделии
    intake_cm: float     # раствор ОДНОЙ вытачки
    length_cm: float     # длина вытачки


@dataclass
class ReconcilePlan:
    method: str               # darts | gather | pleats | conical | ease
    method_title: str
    intake_total_cm: float    # сколько всего убирается по талии
    finished_waist_cm: float  # готовый обхват талии после стыка
    target_waist_cm: float    # требуемый обхват (waist_eff)
    darts: List[Dart] = field(default_factory=list)
    side_take_cm: float = 0.0   # сумма по боковым швам
    gather_ratio: float = 1.0
    pleats: Dict[str, float] = field(default_factory=dict)
    consistent: bool = True
    notes: List[str] = field(default_factory=list)


# распределение раствора как в ядре (patterns.py)
_DART_FRONT_RATIO, _DART_FRONT_MAX, _DART_FRONT_LEN = 0.60, 3.0, 9.0
_DART_BACK_RATIO, _DART_BACK_MAX, _DART_BACK_LEN = 0.65, 3.5, 10.0


def reconcile_waist(assembly: C.Assembly, m: Measurements) -> ReconcilePlan:
    """Превратить талиевый стык сборки в конкретный план: числа вытачек,
    коэффициент сборки или параметры складок."""
    silh = assembly.selection[C.SLOT_SILHOUETTE]
    waist_eff = m.waist_cm + m.ease_waist
    hip_eff = m.hip_cm + m.ease_hip
    skirt_flat = assembly.waist_join["skirt_waist_cm"]

    # --- вытачной крой: раствор уже встроен в геометрию, описываем его ------ #
    if silh in C._WAIST_FITTED_DARTS or silh in C._WAIST_FITTED_YOKE:
        supp_q = max(0.0, (hip_eff - waist_eff) / 4.0)   # раствор на четверть
        df = min(supp_q * _DART_FRONT_RATIO, _DART_FRONT_MAX)
        db = min(supp_q * _DART_BACK_RATIO, _DART_BACK_MAX)
        side_f = max(0.0, supp_q - df)
        side_b = max(0.0, supp_q - db)
        darts = []
        if df > 0.2:
            darts.append(Dart("перед", 2, round(df, 2), _DART_FRONT_LEN))
        if db > 0.2:
            darts.append(Dart("спинка", 2, round(db, 2), _DART_BACK_LEN))
        side_take = round(2.0 * (side_f + side_b), 2)   # 2 боковых шва
        intake = round(hip_eff - waist_eff, 2)
        notes = []
        if silh in C._WAIST_FITTED_YOKE:
            notes.append("Раствор убран в облегающую кокетку (вытачки в кокетке).")
        if not darts:
            notes.append("Раствор мал — убирается только в боковые швы, без вытачек.")
        return ReconcilePlan(
            "darts", "Вытачки + боковые швы", intake, round(waist_eff, 1),
            round(waist_eff, 1), darts=darts, side_take_cm=side_take, notes=notes)

    # --- конический (солнце/полусолнце): срез = талии 1:1 ------------------- #
    if silh in C._WAIST_CONICAL:
        return ReconcilePlan(
            "conical", "Конический крой 1:1", 0.0, round(waist_eff, 1),
            round(waist_eff, 1),
            notes=["Радиальный крой: талиевый срез равен обхвату талии, вытачки не нужны."])

    # --- плиссе: раствор уходит в складки ----------------------------------- #
    if silh in C._WAIST_PLEATED:
        full = getattr(P.PATTERN_REGISTRY.get("pleated"), "fullness", 3.0)
        pleat_w = getattr(P.PATTERN_REGISTRY.get("pleated"), "pleat_width", 3.0)
        n_pleats = max(1, round(waist_eff / pleat_w)) if pleat_w else 0
        depth = round((full - 1.0) * pleat_w / 2.0, 2)   # глубина встречной/ножевой
        intake = round(skirt_flat - waist_eff, 2)
        return ReconcilePlan(
            "pleats", "Складки (плиссе)", intake, round(waist_eff, 1),
            round(waist_eff, 1), gather_ratio=round(full, 2),
            pleats={"count": n_pleats, "depth_cm": depth, "width_cm": round(pleat_w, 2)},
            notes=[f"≈{n_pleats} складок по {pleat_w:g} см, глубина {depth:g} см, заутюжить."])

    # --- сборочный (ярус/баллон/кокетка-сборка): раствор в сборку ----------- #
    if silh in C._WAIST_GATHERED or silh in getattr(C, "_WAIST_RADIAL_GATHERED", set()):
        ratio = round(skirt_flat / waist_eff, 2) if waist_eff else 1.0
        intake = round(skirt_flat - waist_eff, 2)
        return ReconcilePlan(
            "gather", "Сборка по талии", intake, round(waist_eff, 1),
            round(waist_eff, 1), gather_ratio=ratio,
            notes=[f"Проложить 2 строчки сборки, стянуть срез {skirt_flat:g} см "
                   f"до {waist_eff:g} см (×{ratio})."])

    # --- запасной путь ----------------------------------------------------- #
    ratio = round(skirt_flat / waist_eff, 2) if waist_eff else 1.0
    return ReconcilePlan(
        "ease", "Припосадка", round(skirt_flat - waist_eff, 2), round(waist_eff, 1),
        round(waist_eff, 1), gather_ratio=ratio,
        notes=["Силуэт не классифицирован — припосадить срез к поясу."])


# --------------------------------------------------------------------------- #
#  Структурный генератор ТЗ
# --------------------------------------------------------------------------- #
def _piece_role(name: str) -> str:
    n = name.lower()
    if "waist" in n:
        return "пояс/обработка талии"
    if "yoke" in n:
        return "кокетка"
    if "tier" in n:
        return "ярус"
    if "hem" in n:
        return "обработка низа"
    if "shorts" in n:
        return "шорты (подъюбник)"
    if "circle" in n:
        return "полотнище (радиальное)"
    return "основное полотнище"


def build_tech_spec(selection: Dict[str, object], m: Measurements) -> Dict[str, object]:
    """Полное структурированное ТЗ на изделие (dict)."""
    a = C.resolve(selection, m)
    plan = reconcile_waist(a, m)
    sel = a.selection

    silh = sel[C.SLOT_SILHOUETTE]
    closure = sel[C.SLOT_CLOSURE]
    overlay = sel.get(C.SLOT_OVERLAY, "none")
    hem = sel.get(C.SLOT_HEM, "straight")
    wb_key = sel[C.SLOT_WAISTBAND]

    model = {
        "silhouette": C.SILHOUETTE_TITLES.get(silh, silh),
        "waistband": C.WAISTBAND_SPECS.get(wb_key, C.WAISTBAND_SPECS["band"]).title,
        "closure": C.CLOSURE_SPECS[closure].title,
        "overlay": C.OVERLAY_SPECS.get(overlay, C.OVERLAY_SPECS["none"]).title,
        "hem": C.HEM_SPECS.get(hem, C.HEM_SPECS["straight"]).title,
    }

    pieces = [{
        "name": p.name,
        "role": _piece_role(p.name),
        "quantity": p.quantity,
        "cut_on_fold": bool(p.cut_on_fold),
    } for p in a.pieces]

    reconciliation = {
        "method": plan.method,
        "title": plan.method_title,
        "target_waist_cm": plan.target_waist_cm,
        "finished_waist_cm": plan.finished_waist_cm,
        "intake_total_cm": plan.intake_total_cm,
        "side_take_cm": plan.side_take_cm,
        "gather_ratio": plan.gather_ratio,
        "pleats": plan.pleats,
        "darts": [{"location": d.location, "count": d.count,
                   "intake_cm": d.intake_cm, "length_cm": d.length_cm} for d in plan.darts],
        "notes": plan.notes,
    }

    # порядок пошива (зависит от метода стыка/застёжки/деталей)
    steps: List[str] = []
    if plan.method == "darts":
        if plan.darts:
            steps.append("Стачать и заутюжить вытачки на переде и спинке.")
        if plan.side_take_cm > 0.2:
            steps.append("Стачать боковые швы (часть раствора убрана в бок).")
        else:
            steps.append("Стачать боковые швы.")
    elif plan.method == "gather":
        steps.append("Проложить 2 параллельные строчки сборки по талиевому срезу.")
        steps.append("Стачать боковые/вертикальные швы.")
        steps.append(f"Равномерно стянуть сборку до {plan.target_waist_cm:g} см.")
    elif plan.method == "pleats":
        steps.append("Разметить и заложить складки, заутюжить, закрепить по талии.")
        steps.append("Стачать боковые швы по линиям складок.")
    elif plan.method == "conical":
        steps.append("Стачать швы полотнищ; талиевый срез без вытачек (1:1).")
    else:
        steps.append("Подготовить талиевый срез к притачиванию.")

    # застёжка
    if closure == "slit":
        steps.append("Обработать шлицу/разрез.")
    elif closure in ("zip_side", "zip_back"):
        steps.append(f"Втачать потайную молнию ({model['closure'].lower()}), оставив припуск.")
    elif closure == "wrap":
        steps.append("Обработать края запаха, навесить завязки/пуговицу.")

    # пояс
    if wb_key == "elastic":
        steps.append("Сформировать кулису и вставить резинку по обхвату талии.")
    elif wb_key == "facing":
        steps.append("Притачать обтачку по талии, отвернуть и закрепить внутрь.")
    else:
        steps.append("Притачать пояс по верхнему срезу, обработать концы под застёжку.")

    # низ + оверлей
    steps.append({"straight": "Обработать ровный низ подгибкой.",
                  "hi_low": "Обработать асимметричный низ (hi-low) узкой подгибкой/окантовкой.",
                  "ruffle": "Притачать волан по низу и обработать его край."}.get(hem, "Обработать низ."))
    if overlay != "none":
        steps.append(f"Настрочить верхний крой: {model['overlay']} (поверх базы).")

    materials = ["Основная ткань по раскладке", "Дублерин для пояса/обтачки"]
    if closure in ("zip_side", "zip_back"):
        materials.append("Потайная молния")
    if wb_key == "elastic":
        materials.append("Эластичная лента (резинка)")
    materials += ["Нитки в цвет"]

    return {
        "model": model,
        "measurements": {
            "waist_cm": m.waist_cm, "hip_cm": m.hip_cm, "length_cm": m.length_cm,
            "ease_waist": m.ease_waist, "ease_hip": m.ease_hip,
        },
        "seam_allowance_cm": m.seam_allowance,
        "materials": materials,
        "pieces": pieces,
        "waist_reconciliation": reconciliation,
        "construction_order": steps,
        "warnings": a.warnings,
        "_assembly": a,
        "_plan": plan,
    }


def render_spec_markdown(tz: Dict[str, object]) -> str:
    """Человекочитаемое ТЗ (markdown)."""
    md: List[str] = []
    mo = tz["model"]
    me = tz["measurements"]
    rc = tz["waist_reconciliation"]
    md.append(f"# ТЗ на лекало: {mo['silhouette']}")
    md.append("")
    md.append(f"**Модель:** силуэт {mo['silhouette']}; пояс — {mo['waistband']}; "
              f"застёжка — {mo['closure']}; низ — {mo['hem']}; оверлей — {mo['overlay']}.")
    md.append(f"**Мерки:** талия {me['waist_cm']:g}, бёдра {me['hip_cm']:g}, "
              f"длина {me['length_cm']:g} см (приб. талия +{me['ease_waist']:g}, бёдра +{me['ease_hip']:g}).")
    md.append(f"**Припуск на швы:** {tz['seam_allowance_cm']:g} см.")
    md.append("")
    md.append("## Согласование талии")
    md.append(f"- Метод: **{rc['title']}**.")
    md.append(f"- Требуемый обхват талии: {rc['target_waist_cm']:g} см; "
              f"готовый после стыка: {rc['finished_waist_cm']:g} см.")
    if rc["intake_total_cm"]:
        md.append(f"- Убирается по талии всего: {rc['intake_total_cm']:g} см.")
    for d in rc["darts"]:
        md.append(f"- Вытачки ({d['location']}): {d['count']} шт × раствор {d['intake_cm']:g} см, "
                  f"длина {d['length_cm']:g} см.")
    if rc["side_take_cm"]:
        md.append(f"- В боковые швы: {rc['side_take_cm']:g} см.")
    if rc["gather_ratio"] and rc["gather_ratio"] != 1.0:
        md.append(f"- Коэффициент сборки/раскладки: ×{rc['gather_ratio']:g}.")
    if rc["pleats"]:
        pl = rc["pleats"]
        md.append(f"- Складки: ≈{pl.get('count')} шт по {pl.get('width_cm'):g} см, "
                  f"глубина {pl.get('depth_cm'):g} см.")
    for n in rc["notes"]:
        md.append(f"  - {n}")
    md.append("")
    md.append("## Детали кроя")
    for p in tz["pieces"]:
        fold = " (по сгибу)" if p["cut_on_fold"] else ""
        md.append(f"- {p['name']} — {p['role']}, ×{p['quantity']}{fold}")
    md.append("")
    md.append("## Материалы")
    for x in tz["materials"]:
        md.append(f"- {x}")
    md.append("")
    md.append("## Порядок пошива")
    for i, s in enumerate(tz["construction_order"], 1):
        md.append(f"{i}. {s}")
    if tz["warnings"]:
        md.append("")
        md.append("## Предупреждения")
        for w in tz["warnings"]:
            md.append(f"- ⚠ {w}")
    return "\n".join(md)


# --------------------------------------------------------------------------- #
#  verify_assembly: сшиваемо ли собранное из частей лекало
# --------------------------------------------------------------------------- #
@dataclass
class AssemblyCheck:
    ok: bool
    fails: List[str] = field(default_factory=list)
    warns: List[str] = field(default_factory=list)
    infos: List[str] = field(default_factory=list)


def verify_assembly(selection: Dict[str, object], m: Measurements,
                    export_prefix: Optional[str] = None) -> AssemblyCheck:
    """Проверка собранного из частей лекала: геометрия, припуск, сходимость
    талиевого стыка, надевание, экспорт. Переиспользует геометрию verify_sewable."""
    import verify_sewable as V   # переиспользуем проверенные геом-хелперы

    res = AssemblyCheck(ok=True)
    a = C.resolve(selection, m)
    plan = reconcile_waist(a, m)
    waist_eff = m.waist_cm + m.ease_waist
    hip_eff = m.hip_cm + m.ease_hip
    body = [p for p in a.pieces if p.name != "waistband"]

    # 1) геометрия каждой детали
    for p in a.pieces:
        pts = p.points
        if pts[0] != pts[-1]:
            res.fails.append(f"{p.name}: контур не замкнут"); continue
        if V._area(pts) < 5:
            res.fails.append(f"{p.name}: площадь почти нулевая"); continue
        if V._min_edge(pts) < 0.05:
            res.fails.append(f"{p.name}: нулевое ребро"); continue
        if not V._is_simple(pts):
            res.fails.append(f"{p.name}: самопересечение"); continue
    if not res.fails:
        res.infos.append(f"геометрия всех {len(a.pieces)} деталей корректна")

    # 2) припуск реально добавляется
    grew = sum(1 for p in body
               if V._area(export.seam_outline(p.points, m.seam_allowance)) > V._area(p.points) + 1)
    if grew == len(body):
        res.infos.append(f"припуск {m.seam_allowance:g} см растит контур всех {grew} деталей")
    else:
        res.fails.append(f"припуск добавлен только на {grew}/{len(body)}")

    # 3) сходимость талиевого стыка
    if abs(plan.finished_waist_cm - waist_eff) <= 1.0:
        res.infos.append(f"талиевый стык сходится: готовый {plan.finished_waist_cm:g} = талия {waist_eff:g} см")
    else:
        res.fails.append(f"талиевый стык НЕ сходится: {plan.finished_waist_cm:g} vs {waist_eff:g}")
    if plan.method == "darts" and plan.darts:
        removed = sum(d.count * d.intake_cm for d in plan.darts) + plan.side_take_cm
        if abs(removed - plan.intake_total_cm) <= 1.0:
            res.infos.append(f"раствор сходится: вытачки+бок {removed:.1f} = {plan.intake_total_cm:g} см")
        else:
            res.warns.append(f"раствор: вытачки+бок {removed:.1f} ≠ {plan.intake_total_cm:g} см")

    # 4) надевание: ткань по бёдрам не меньше тела
    fold_w = 0.0
    for p in body:
        w, _ = V._bbox(p.points)
        fold_w += w * (2 if p.cut_on_fold else 1) * max(1, p.quantity if not p.cut_on_fold else 1)
    if fold_w + 0.5 >= m.hip_cm:
        res.infos.append(f"ткань по обхвату {fold_w:.0f} см ≥ бёдра {m.hip_cm:g} → наденется")
    else:
        res.warns.append(f"ткань по обхвату {fold_w:.0f} см < бёдра {m.hip_cm:g} — проверить надевание")

    # 5) экспорт
    if export_prefix:
        svg = f"/data/skirt/{export_prefix}.svg"
        pdf = f"/data/skirt/{export_prefix}.pdf"
        w, h = export.export_svg(a.pieces, svg)
        rows, cols = export.export_pdf_tiled(a.pieces, pdf)
        if (os.path.exists(svg) and os.path.getsize(svg) > 200
                and os.path.exists(pdf) and os.path.getsize(pdf) > 500
                and w > 0 and h > 0):
            res.infos.append(f"экспорт OK: раскладка {w:.0f}×{h:.0f} см, A4 {rows}×{cols} листов")
        else:
            res.fails.append("экспорт SVG/PDF не удался")

    res.ok = not res.fails
    return res
