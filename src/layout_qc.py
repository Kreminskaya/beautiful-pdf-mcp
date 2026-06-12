"""Постраничный QC вёрстки — механизм «страница = блок» (docs/SPEC_PAGE_FILL.md).

Меряет готовые PNG-страницы против паспорта страницы шаблона (page_contract
в data/styles.json) и возвращает числовой отчёт по каждой странице:
заполненность полосы набора, недолив в строках и словах, внутренние дыры,
баланс колонок. Шаблонной логики здесь нет — все различия жанров приходят
из паспорта.
"""
from __future__ import annotations

import json
import statistics
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

PAPER_MM = {
    "a4": (210.0, 297.0),
    "a5": (148.0, 210.0),
    "a3": (297.0, 420.0),
    "us-letter": (215.9, 279.4),
}

INK_THRESHOLD = 200  # grayscale: темнее — считается «чернилами»

DEFAULT_CONTRACT = {
    "columns": 1,
    # true — секции начинаются с нового листа (книга-главы, ГОСТ-разделы):
    # страница ПЕРЕД началом секции — легально частичная
    "section_breaks": False,
    # политика последней страницы потока: "min_fill" | "partial_ok" | "balance_columns"
    "final_page_policy": "min_fill",
    "min_final_fill": 0.5,
    # сколько строк недолива терпимо на странице внутри потока
    "underfill_tolerance_lines": 1.5,
    # внутренняя дыра больше стольких строк — дефект (вне exempt-страниц)
    "max_hole_lines": 3.0,
    # допустимая разница низа колонок (для columns: 2), в строках
    "column_balance_lines": 3.0,
}

FALLBACK_LEADING_MM = 4.6  # если на странице мало строк для самокалибровки

# версия алгоритма замера: входит в ключ кэша калибровки
QC_VERSION = 2


def parse_len_mm(value: str) -> float:
    """'2.5cm' | '25mm' | '12pt' → мм."""
    s = str(value).strip()
    if s.endswith("cm"):
        return float(s[:-2]) * 10.0
    if s.endswith("mm"):
        return float(s[:-2])
    if s.endswith("pt"):
        return float(s[:-2]) * 25.4 / 72.0
    return float(s)  # голое число трактуем как мм


def load_contract(styles_file: Path, template: str) -> dict:
    contract = dict(DEFAULT_CONTRACT)
    try:
        styles = json.loads(Path(styles_file).read_text(encoding="utf-8"))
        contract.update(styles["presets"][template].get("page_contract", {}))
    except Exception:
        pass
    return contract


def geometry_from_preset(preset: dict) -> dict:
    """Полоса набора в мм из плоского пресета документа (истина для всех шаблонов)."""
    paper = preset.get("paper", "a4")
    w, h = PAPER_MM.get(paper, PAPER_MM["a4"])
    return {
        "paper_w": w,
        "paper_h": h,
        "m_top": parse_len_mm(preset.get("margin_top", "2.5cm")),
        "m_bottom": parse_len_mm(preset.get("margin_bottom", "2.5cm")),
        "m_left": parse_len_mm(preset.get("margin_left", "2.5cm")),
        "m_right": parse_len_mm(preset.get("margin_right", "2.5cm")),
    }


def _runs(flags: np.ndarray) -> list[tuple[int, int]]:
    """Непрерывные отрезки True → [(start, end_inclusive), ...]."""
    out = []
    start = None
    for i, f in enumerate(flags):
        if f and start is None:
            start = i
        elif not f and start is not None:
            out.append((start, i - 1))
            start = None
    if start is not None:
        out.append((start, len(flags) - 1))
    return out


def measure_page(png_path: str | Path, geom: dict) -> dict:
    """Сырые метрики одной страницы: где чернила относительно полосы набора."""
    img = np.array(Image.open(png_path).convert("L"))
    h_px, w_px = img.shape
    ppm = h_px / geom["paper_h"]  # px на мм (масштаб любого ppi)

    ta_top = round(geom["m_top"] * ppm)
    ta_bot = round((geom["paper_h"] - geom["m_bottom"]) * ppm)
    ta_l = round(geom["m_left"] * ppm)
    ta_r = round((geom["paper_w"] - geom["m_right"]) * ppm)
    # +3мм слабины снизу: свисающие выносные элементы — не дефект
    crop = img[ta_top:min(h_px, ta_bot + round(3 * ppm)), ta_l:ta_r]
    ta_h_mm = (ta_bot - ta_top) / ppm

    row_ink = crop.min(axis=1) < INK_THRESHOLD
    if not row_ink.any():
        return {"empty": True, "ta_h_mm": ta_h_mm}

    rows = np.where(row_ink)[0]
    first, last = int(rows.min()), int(rows.max())
    raw_runs = _runs(row_ink)
    # склеиваем полосы с зазором <1мм: белые щели внутри глифов — не межстрочье
    min_gap_px = max(1, round(1.0 * ppm))
    line_runs = []
    for s, e in raw_runs:
        if line_runs and s - line_runs[-1][1] - 1 < min_gap_px:
            line_runs[-1] = (line_runs[-1][0], e)
        else:
            line_runs.append((s, e))
    starts = [s for s, _ in line_runs]
    leading_mm = None
    if len(starts) >= 4:
        gaps = [(b - a) / ppm for a, b in zip(starts, starts[1:])]
        # межстрочный шаг: медиана физичных интервалов (2–12мм);
        # большие — абзацы/картинки, меньшие — артефакты растра
        plausible = [g for g in gaps if 2.0 <= g <= 12.0]
        if len(plausible) >= 3:
            leading_mm = statistics.median(plausible)

    bottom_gap_mm = max(0.0, ta_h_mm - (last + 1) / ppm)
    fill = min(1.0, ((last + 1) / ppm) / ta_h_mm)

    # максимальная внутренняя дыра между первым и последним чернильным рядом
    max_hole_mm = 0.0
    hole_at_mm = None
    for (_, end_prev), (start_next, _) in zip(line_runs, line_runs[1:]):
        hole = (start_next - end_prev - 1) / ppm
        if hole > max_hole_mm:
            max_hole_mm = hole
            hole_at_mm = (end_prev + 1) / ppm

    # колонки: ищем сплошную белую вертикальную «канаву» ≥5мм в средней зоне
    col_bottoms_mm = None
    col_ink = (crop < INK_THRESHOLD).any(axis=0)
    gutters = [(s, e) for s, e in _runs(~col_ink)
               if (e - s + 1) / ppm >= 5.0
               and 0.15 < (s + e) / 2 / crop.shape[1] < 0.85]
    if gutters:
        s, e = max(gutters, key=lambda g: g[1] - g[0])
        halves = [crop[:, :s], crop[:, e + 1:]]
        bottoms = []
        for half in halves:
            r = np.where((half < INK_THRESHOLD).any(axis=1))[0]
            bottoms.append(((int(r.max()) + 1) / ppm) if r.size else 0.0)
        col_bottoms_mm = bottoms

    return {
        "empty": False,
        "ta_h_mm": round(ta_h_mm, 1),
        "fill": round(fill, 3),
        "bottom_gap_mm": round(bottom_gap_mm, 1),
        "top_offset_mm": round(first / ppm, 1),
        "n_lines": len(line_runs),
        "leading_mm": round(leading_mm, 2) if leading_mm else None,
        "max_hole_mm": round(max_hole_mm, 1),
        "hole_at_mm": round(hole_at_mm, 1) if hole_at_mm is not None else None,
        "col_bottoms_mm": col_bottoms_mm,
    }


def query_para_positions(main_typ: Path, fonts_dir: Path, cwd: Path) -> list[dict] | None:
    """Позиции абзацев из меток <bp-para> — для двухпасовой компиляции (§3.5).

    Возвращает список {sec, para, page, y_mm} отсортированный по (sec, para).
    y_mm — расстояние от верха страницы в мм.
    """
    try:
        result = subprocess.run(
            ["typst", "query", "--font-path", str(fonts_dir),
             str(main_typ), "<bp-para>", "--field", "value"],
            capture_output=True, text=True, cwd=str(cwd), timeout=120,
        )
        if result.returncode != 0:
            return None
        values = json.loads(result.stdout)
        out = []
        for v in values:
            if not isinstance(v, dict) or "pos" not in v:
                continue
            pos = v["pos"]
            if not isinstance(pos, dict) or "page" not in pos:
                continue
            y_raw = pos.get("y", "0pt")
            y_pt = float(str(y_raw).replace("pt", "")) if isinstance(y_raw, str) else float(y_raw)
            out.append({
                "sec":  int(v.get("sec",  0)),
                "para": int(v.get("para", 0)),
                "page": int(pos["page"]),
                "y_mm": round(y_pt * 25.4 / 72.0, 2),
            })
        return sorted(out, key=lambda x: (x["sec"], x["para"])) or None
    except Exception:
        return None


def query_section_pages(main_typ: Path, fonts_dir: Path, cwd: Path) -> list[int] | None:
    """Страницы, где начинаются секции верхнего уровня (метки <bp-sec> в шаблонах)."""
    try:
        result = subprocess.run(
            ["typst", "query", "--font-path", str(fonts_dir),
             str(main_typ), "<bp-sec>", "--field", "value"],
            capture_output=True, text=True, cwd=str(cwd), timeout=120,
        )
        if result.returncode != 0:
            return None
        values = json.loads(result.stdout)
        pages = sorted({int(v["page"]) for v in values if isinstance(v, dict) and "page" in v})
        return pages or None
    except Exception:
        return None


def analyze_document(png_paths: list, preset: dict, contract: dict,
                     section_pages: list[int] | None = None,
                     words_per_line: float | None = None) -> dict:
    """Отчёт «страница = блок» по всему документу. ok=False — есть дефекты вёрстки."""
    geom = geometry_from_preset(preset)
    n = len(png_paths)
    content_start = min(section_pages) if section_pages else 1
    section_starts = set(section_pages or [])

    final_pages = {n}
    if contract.get("section_breaks") and section_pages:
        for p in section_pages:
            if p - 1 >= content_start:
                final_pages.add(p - 1)

    pages_report = []
    for i, path in enumerate(png_paths, start=1):
        if i < content_start:
            pages_report.append({"page": i, "verdict": "FRONT_MATTER"})
            continue

        m = measure_page(path, geom)
        if m["empty"]:
            pages_report.append({"page": i, "verdict": "EMPTY",
                                 "issues": ["страница без контента"]})
            continue

        leading = m["leading_mm"] or FALLBACK_LEADING_MM
        lines_short = m["bottom_gap_mm"] / leading
        issues = []
        entry = {
            "page": i,
            "fill": m["fill"],
            "bottom_gap_mm": m["bottom_gap_mm"],
            "lines_short": round(lines_short, 1),
            "max_hole_mm": m["max_hole_mm"],
            "leading_mm": round(leading, 2),
        }

        is_final = i in final_pages
        is_section_start = i in section_starts

        # колонки (resume): баланс низа
        if contract.get("columns", 1) == 2 and m.get("col_bottoms_mm"):
            left, right = m["col_bottoms_mm"]
            diff_lines = abs(left - right) / leading
            entry["column_diff_lines"] = round(diff_lines, 1)
            if diff_lines > contract["column_balance_lines"]:
                issues.append(
                    f"колонки не сбалансированы: разница {diff_lines:.1f} строк "
                    f"(допуск {contract['column_balance_lines']})")
            # недолив страницы меряем по более длинной колонке
            lines_short = (m["ta_h_mm"] - max(left, right)) / leading
            entry["lines_short"] = round(max(0.0, lines_short), 1)

        # недолив
        if lines_short > contract["underfill_tolerance_lines"]:
            words = (f" (~{round(lines_short * words_per_line)} слов)"
                     if words_per_line else "")
            if is_final:
                policy = contract.get("final_page_policy", "min_fill")
                if policy == "min_fill" and m["fill"] < contract["min_final_fill"]:
                    issues.append(
                        f"финальная страница потока заполнена на {m['fill']:.0%} "
                        f"< {contract['min_final_fill']:.0%}: добавить "
                        f"~{lines_short:.0f} строк{words} или оформить концовку")
                # partial_ok / balance_columns: частичный финал легален
            else:
                issues.append(
                    f"недолив {lines_short:.1f} строк до низа полосы{words}")

        # внутренние дыры (страница начала секции — exempt: воздух заголовка/фронтисписа)
        if (not is_section_start
                and m["max_hole_mm"] > contract["max_hole_lines"] * leading):
            issues.append(
                f"внутренняя дыра {m['max_hole_mm']:.0f}мм "
                f"(>{contract['max_hole_lines']:.0f} строк) "
                f"на {m['hole_at_mm']:.0f}мм от верха полосы")

        entry["issues"] = issues
        entry["verdict"] = "OK" if not issues else "DEFECT"
        pages_report.append(entry)

    bad = [p for p in pages_report if p["verdict"] not in ("OK", "FRONT_MATTER")]
    return {
        "ok": not bad,
        "pages": pages_report,
        "summary": ("вёрстка чистая: все страницы заполнены по паспорту шаблона"
                    if not bad else
                    f"дефекты на страницах: {', '.join(str(p['page']) for p in bad)}"),
    }
