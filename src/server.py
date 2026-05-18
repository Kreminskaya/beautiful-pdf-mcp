"""Beautiful PDF MCP Server — generates typographically clean PDFs via Typst."""

import json
import re
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

from fastmcp import FastMCP
from PIL import Image

mcp = FastMCP("beautiful-pdf")

# In-memory document store: doc_id → DocumentState
_docs: dict[str, dict] = {}

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
ASSETS_DIR = Path(__file__).parent.parent / "assets"
FONTS_DIR = Path(__file__).parent.parent / "assets" / "fonts"
STYLES_FILE = Path(__file__).parent.parent / "data" / "styles.json"


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _load_preset(template: str) -> dict:
    """Load style preset from styles.json, returns flat dict for template use."""
    try:
        styles = json.loads(STYLES_FILE.read_text(encoding="utf-8"))
        presets = styles.get("presets", {})
        preset = presets.get(template) or presets.get("report", {})
    except Exception:
        return {}

    fonts = preset.get("fonts", {})
    colors = preset.get("colors", {})
    text_cfg = preset.get("text", {})
    page_cfg = preset.get("page", {})
    margin = page_cfg.get("margin", {})
    headings = preset.get("headings", {})

    return {
        "body_font": fonts.get("body", "PT Serif"),
        "heading_font": fonts.get("heading", "PT Sans"),
        "mono_font": fonts.get("mono", "Source Code Pro"),
        "text_size": text_cfg.get("size", "10.5pt"),
        "leading": text_cfg.get("leading", "0.65em"),
        "justify": text_cfg.get("justify", True),
        "hyphenate": text_cfg.get("hyphenate", True),
        "paper": page_cfg.get("paper", "a4"),
        "margin_left": margin.get("left", "2.5cm"),
        "margin_right": margin.get("right", "2.5cm"),
        "margin_top": margin.get("top", "2.5cm"),
        "margin_bottom": margin.get("bottom", "2.5cm"),
        "accent_color": colors.get("accent", "#1d3557"),
        "heading_color": colors.get("heading", "#1a1a1a"),
        "body_color": colors.get("body", "#1a1a1a"),
        "muted_color": colors.get("muted", "#64748b"),
        "h1_size": headings.get("h1_size", "16pt"),
        "h2_size": headings.get("h2_size", "13pt"),
        "h3_size": headings.get("h3_size", "11pt"),
        "h1_weight": headings.get("h1_weight", "bold"),
        "h2_weight": headings.get("h2_weight", "semibold"),
        "h3_weight": headings.get("h3_weight", "semibold"),
        "numbered_headings": headings.get("numbered", True),
        "show_toc": preset.get("toc", True),
        "show_header_footer": preset.get("header_footer", True),
        "indent": preset.get("indent", ""),
        "chapter_break": preset.get("chapter_break", False),
    }


def _md_to_typst(text: str) -> str:
    """Convert Markdown to Typst markup (subset: bold, italic, inline code, links).

    Handles # escaping properly: bare # (hex colors, anchors) are escaped,
    but #link(...) calls we insert are preserved.
    """
    # Protect inline code spans from # escaping
    code_spans: dict[str, str] = {}

    def protect_code(m: re.Match) -> str:
        key = f"\x00CODE{len(code_spans)}\x00"
        code_spans[key] = f"`{m.group(1)}`"
        return key

    text = re.sub(r"`([^`]+)`", protect_code, text)

    # Bold **text**
    text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)
    # Italic *text* or _text_
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"_\1_", text)
    text = re.sub(r"(?<!_)_(?!_)(.+?)(?<!_)_(?!_)", r"_\1_", text)
    # Links [text](url) → Typst #link — BEFORE escaping # so we can protect them
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r'#link("\2")[\1]', text)
    # Escape all # that are not part of #link() we just inserted
    text = re.sub(r"(?<!\\)#(?!link\()", r"\\#", text)

    # Restore inline code
    for key, val in code_spans.items():
        text = text.replace(key, val)

    return text


def _image_width_to_typst(width_hint: str) -> str:
    mapping = {
        "full": "100%",
        "half": "50%",
        "third": "33%",
        "quarter": "25%",
        "large": "80%",
    }
    if width_hint in mapping:
        return mapping[width_hint]
    return width_hint


def _copy_image_to_assets(img_path: Path, assets_dir: Path) -> str:
    """Copy image to assets dir, return relative path for Typst."""
    if img_path.exists() and not (assets_dir / img_path.name).exists():
        shutil.copy2(img_path, assets_dir / img_path.name)
    return f"assets/{img_path.name}"


def _compile_typst(doc_id: str, output_format: str = "pdf") -> Path:
    """Compile the document to PDF or PNG preview. Returns output path."""
    doc = _docs[doc_id]
    work_dir = Path(doc["work_dir"])
    assets_dir = work_dir / "assets"
    assets_dir.mkdir(exist_ok=True)

    # Copy referenced images into assets (sections → images and galleries)
    for section in doc.get("sections", []):
        for img in section.get("images", []):
            src = Path(img["path"])
            img["_local"] = _copy_image_to_assets(src, assets_dir)

        for gallery in section.get("galleries", []):
            for img in gallery.get("images", []):
                src = Path(img["path"])
                img["_local"] = _copy_image_to_assets(src, assets_dir)

    # Write content JSON
    content_json = json.dumps(doc, ensure_ascii=False, indent=2)
    (assets_dir / "content.json").write_text(content_json, encoding="utf-8")

    # Copy template
    template = doc.get("template", "report")
    tmpl_path = TEMPLATES_DIR / f"{template}.typ"
    if not tmpl_path.exists():
        tmpl_path = TEMPLATES_DIR / "report.typ"

    main_typ = work_dir / "main.typ"
    main_typ.write_text(tmpl_path.read_text(encoding="utf-8"), encoding="utf-8")

    for f in TEMPLATES_DIR.glob("*.typ"):
        dest = work_dir / f.name
        if not dest.exists() or f.name != "main.typ":
            shutil.copy2(f, dest)

    if output_format == "pdf":
        out_path = work_dir / "output.pdf"
        cmd = ["typst", "compile",
               "--font-path", str(FONTS_DIR),
               str(main_typ), str(out_path)]
    else:
        out_path = work_dir / "preview.png"
        cmd = ["typst", "compile",
               "--font-path", str(FONTS_DIR),
               "--format", "png", "--pages", "1",
               str(main_typ), str(out_path)]

    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=str(work_dir)
    )

    if result.returncode != 0:
        raise RuntimeError(f"Typst error:\n{result.stderr}")

    return out_path


def _find_section(doc_id: str, section_id: str) -> dict:
    for section in _docs[doc_id]["sections"]:
        if section["id"] == section_id:
            return section
    raise ValueError(f"Section {section_id} not found in document {doc_id}")


# ─── MCP Tools ────────────────────────────────────────────────────────────────

@mcp.tool()
def create_document(
    title: str,
    author: str = "",
    template: str = "report",
    language: str = "ru",
    preset_overrides: dict | None = None,
) -> dict:
    """Create a new document. Returns doc_id.

    template: report | academic_ru | book | technical | portfolio | letter
    language: ru | en
    preset_overrides: optional dict to customise any typographic parameter, e.g.:
      {"accent_color": "#e63946", "body_font": "PT Serif", "show_toc": false}
    Overridable keys: accent_color, heading_color, muted_color, body_color,
      body_font, heading_font, mono_font, text_size, h1_size, h2_size, h3_size,
      margin_left, margin_right, margin_top, margin_bottom, leading,
      show_toc, show_header_footer, numbered_headings.
    """
    doc_id = str(uuid.uuid4())[:8]
    work_dir = Path(tempfile.mkdtemp(prefix=f"pdf_{doc_id}_"))
    preset = _load_preset(template)
    if preset_overrides:
        preset.update(preset_overrides)

    _docs[doc_id] = {
        "doc_id": doc_id,
        "title": title,
        "author": author,
        "template": template,
        "language": language,
        "preset": preset,
        "sections": [],
        "work_dir": str(work_dir),
    }

    return {"doc_id": doc_id, "template": template, "preset_loaded": bool(preset)}


@mcp.tool()
def add_section(
    doc_id: str,
    title: str,
    content: str,
    level: int = 1,
    numbered: bool = True,
) -> dict:
    """Add a section with Markdown content.

    level: 1=chapter, 2=section, 3=subsection
    content: Markdown text (bold, italic, inline code, links supported)
    """
    if doc_id not in _docs:
        raise ValueError(f"Document {doc_id} not found")

    section_id = str(uuid.uuid4())[:6]
    section = {
        "id": section_id,
        "title": title,
        "content": _md_to_typst(content),
        "level": level,
        "numbered": numbered,
        "images": [],
        "galleries": [],
        "tables": [],
        "code_blocks": [],
        "callouts": [],
    }
    _docs[doc_id]["sections"].append(section)
    return {"section_id": section_id, "title": title}


@mcp.tool()
def update_section(
    doc_id: str,
    section_id: str,
    title: str = "",
    content: str = "",
) -> dict:
    """Update the title or content of an existing section.

    Pass only the fields you want to change.
    """
    if doc_id not in _docs:
        raise ValueError(f"Document {doc_id} not found")

    section = _find_section(doc_id, section_id)
    if title:
        section["title"] = title
    if content:
        section["content"] = _md_to_typst(content)
    return {"section_id": section_id, "updated": True}


@mcp.tool()
def remove_section(doc_id: str, section_id: str) -> dict:
    """Remove a section (and all its content) from the document."""
    if doc_id not in _docs:
        raise ValueError(f"Document {doc_id} not found")

    sections = _docs[doc_id]["sections"]
    before = len(sections)
    _docs[doc_id]["sections"] = [s for s in sections if s["id"] != section_id]
    if len(_docs[doc_id]["sections"]) == before:
        raise ValueError(f"Section {section_id} not found")
    return {"removed": section_id}


@mcp.tool()
def add_image(
    doc_id: str,
    section_id: str,
    path: str,
    caption: str = "",
    width: str = "full",
    position: str = "center",
) -> dict:
    """Add an image to a section.

    path: absolute path to image file (PNG, JPG, SVG)
    width: full | half | third | quarter | large | "80%"
    position: center | left | right
    """
    if doc_id not in _docs:
        raise ValueError(f"Document {doc_id} not found")

    img_path = Path(path)
    if not img_path.exists():
        raise ValueError(f"Image not found: {path}")

    try:
        with Image.open(img_path) as im:
            w, h = im.size
            aspect = round(h / w, 3)
    except Exception:
        aspect = 0.75

    img_id = str(uuid.uuid4())[:6]
    img_data = {
        "id": img_id,
        "path": str(img_path.resolve()),
        "filename": img_path.name,
        "caption": caption,
        "width": _image_width_to_typst(width),
        "position": position,
        "aspect": aspect,
    }

    section = _find_section(doc_id, section_id)
    section["images"].append(img_data)
    return {"image_id": img_id, "filename": img_path.name}


@mcp.tool()
def add_gallery(
    doc_id: str,
    section_id: str,
    paths: list,
    columns: int = 2,
    caption: str = "",
) -> dict:
    """Add a grid of images to a section — the images are distributed evenly across columns.

    paths: list of absolute paths to image files (PNG, JPG, SVG)
    columns: number of columns in the grid (1–4)
    caption: optional caption for the whole gallery

    Use this instead of multiple add_image calls when you have 3+ images
    that should be displayed together (portfolio work, photo sets, comparisons).
    """
    if doc_id not in _docs:
        raise ValueError(f"Document {doc_id} not found")

    columns = max(1, min(4, columns))
    images = []
    for p in paths:
        img_path = Path(p)
        if not img_path.exists():
            raise ValueError(f"Image not found: {p}")
        try:
            with Image.open(img_path) as im:
                w, h = im.size
                aspect = round(h / w, 3)
        except Exception:
            aspect = 0.75
        images.append({
            "id": str(uuid.uuid4())[:6],
            "path": str(img_path.resolve()),
            "filename": img_path.name,
            "aspect": aspect,
        })

    gallery_id = str(uuid.uuid4())[:6]
    gallery_data = {
        "id": gallery_id,
        "images": images,
        "columns": columns,
        "caption": caption,
    }

    section = _find_section(doc_id, section_id)
    section["galleries"].append(gallery_data)
    return {"gallery_id": gallery_id, "images_count": len(images), "columns": columns}


@mcp.tool()
def add_table(
    doc_id: str,
    section_id: str,
    headers: list,
    rows: list,
    caption: str = "",
) -> dict:
    """Add a table to a section.

    headers: list of column names
    rows: list of rows, each row is a list of cell values
    """
    if doc_id not in _docs:
        raise ValueError(f"Document {doc_id} not found")

    table_id = str(uuid.uuid4())[:6]
    table_data = {
        "id": table_id,
        "headers": headers,
        "rows": rows,
        "caption": caption,
    }

    section = _find_section(doc_id, section_id)
    section["tables"].append(table_data)
    return {"table_id": table_id}


@mcp.tool()
def add_code_block(
    doc_id: str,
    section_id: str,
    code: str,
    language: str = "",
    caption: str = "",
) -> dict:
    """Add a code block to a section."""
    if doc_id not in _docs:
        raise ValueError(f"Document {doc_id} not found")

    cb_id = str(uuid.uuid4())[:6]
    cb_data = {"id": cb_id, "code": code, "language": language, "caption": caption}

    section = _find_section(doc_id, section_id)
    section["code_blocks"].append(cb_data)
    return {"code_block_id": cb_id}


@mcp.tool()
def add_callout(
    doc_id: str,
    section_id: str,
    text: str,
    kind: str = "info",
) -> dict:
    """Add a callout box to a section.

    kind: info | warning | tip | danger | quote
    """
    if doc_id not in _docs:
        raise ValueError(f"Document {doc_id} not found")

    callout_id = str(uuid.uuid4())[:6]
    callout_data = {"id": callout_id, "text": _md_to_typst(text), "kind": kind}

    section = _find_section(doc_id, section_id)
    section["callouts"].append(callout_data)
    return {"callout_id": callout_id}


@mcp.tool()
def compile_preview(doc_id: str) -> dict:
    """Compile a PNG preview of the first page. Use to check layout before final PDF."""
    if doc_id not in _docs:
        raise ValueError(f"Document {doc_id} not found")

    out_path = _compile_typst(doc_id, output_format="png")
    return {
        "preview_path": str(out_path),
        "message": f"Preview saved to {out_path}. Open it to check layout.",
    }


@mcp.tool()
def compile_pdf(doc_id: str, output_path: str = "") -> dict:
    """Compile the final PDF. Optionally specify output_path."""
    if doc_id not in _docs:
        raise ValueError(f"Document {doc_id} not found")

    pdf_path = _compile_typst(doc_id, output_format="pdf")

    if output_path:
        dest = Path(output_path).expanduser()
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pdf_path, dest)
        pdf_path = dest

    return {
        "pdf_path": str(pdf_path),
        "message": f"PDF ready: {pdf_path}",
    }


@mcp.tool()
def save_document(doc_id: str, path: str) -> dict:
    """Save the document state to a JSON file so it can be restored after a restart.

    path: absolute path where the JSON should be saved (e.g. ~/Desktop/report.json)
    """
    if doc_id not in _docs:
        raise ValueError(f"Document {doc_id} not found")

    dest = Path(path).expanduser()
    dest.parent.mkdir(parents=True, exist_ok=True)

    export = {k: v for k, v in _docs[doc_id].items() if k != "work_dir"}
    dest.write_text(json.dumps(export, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"saved_to": str(dest), "sections": len(_docs[doc_id]["sections"])}


@mcp.tool()
def load_document(path: str) -> dict:
    """Load a previously saved document from a JSON file.

    Returns doc_id that can be used immediately for compile_preview / compile_pdf.
    """
    src = Path(path).expanduser()
    if not src.exists():
        raise ValueError(f"File not found: {path}")

    data = json.loads(src.read_text(encoding="utf-8"))
    doc_id = data.get("doc_id", str(uuid.uuid4())[:8])
    work_dir = Path(tempfile.mkdtemp(prefix=f"pdf_{doc_id}_"))

    data["work_dir"] = str(work_dir)
    _docs[doc_id] = data

    return {
        "doc_id": doc_id,
        "title": data.get("title", ""),
        "sections": len(data.get("sections", [])),
        "template": data.get("template", "report"),
    }


@mcp.tool()
def list_documents() -> dict:
    """List all active documents in this session."""
    return {
        "documents": [
            {"doc_id": d["doc_id"], "title": d["title"], "sections": len(d["sections"])}
            for d in _docs.values()
        ]
    }


@mcp.tool()
def get_document_state(doc_id: str) -> dict:
    """Get the current state of a document (sections, images, etc.)."""
    if doc_id not in _docs:
        raise ValueError(f"Document {doc_id} not found")
    doc = dict(_docs[doc_id])
    doc.pop("work_dir", None)
    return doc


if __name__ == "__main__":
    mcp.run()
