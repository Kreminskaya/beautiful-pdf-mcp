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
    """Convert Markdown to Typst markup (subset: bold, italic, inline code, links)."""
    # Bold **text**
    text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)
    # Italic *text* or _text_
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"_\1_", text)
    text = re.sub(r"(?<!_)_(?!_)(.+?)(?<!_)_(?!_)", r"_\1_", text)
    # Inline code `code`
    text = re.sub(r"`([^`]+)`", r"`\1`", text)
    # Links [text](url) → text (Typst links need #link)
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r'#link("\2")[\1]', text)
    # Escape # at start of line (Typst headings conflict)
    text = re.sub(r"^#", r"\#", text, flags=re.MULTILINE)
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
    # Already a percentage or absolute value
    return width_hint


def _build_typst(doc: dict, assets_dir: Path) -> str:
    """Generate a .typ file content from the document state."""
    template = doc.get("template", "report")
    tmpl_path = TEMPLATES_DIR / f"{template}.typ"
    if not tmpl_path.exists():
        tmpl_path = TEMPLATES_DIR / "report.typ"

    content_json = json.dumps(doc, ensure_ascii=False, indent=2)
    (assets_dir / "content.json").write_text(content_json, encoding="utf-8")

    return tmpl_path.read_text(encoding="utf-8")


def _compile_typst(doc_id: str, output_format: str = "pdf") -> Path:
    """Compile the document to PDF or PNG preview. Returns output path."""
    doc = _docs[doc_id]
    work_dir = Path(doc["work_dir"])
    assets_dir = work_dir / "assets"
    assets_dir.mkdir(exist_ok=True)

    # Copy any referenced images into assets
    for section in doc.get("sections", []):
        for img in section.get("images", []):
            src = Path(img["path"])
            if src.exists() and not (assets_dir / src.name).exists():
                shutil.copy2(src, assets_dir / src.name)
            # Use path relative to work_dir so Typst resolves it correctly
            # (avoids macOS /tmp → /private/tmp symlink confusion)
            img["_local"] = f"assets/{src.name}"

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

    # Copy shared template helpers
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


# ─── MCP Tools ────────────────────────────────────────────────────────────────

@mcp.tool()
def create_document(
    title: str,
    author: str = "",
    template: str = "report",
    language: str = "ru",
) -> dict:
    """Create a new document. Returns doc_id.

    template: report | academic_ru | book | technical | portfolio | letter
    language: ru | en
    """
    doc_id = str(uuid.uuid4())[:8]
    work_dir = Path(tempfile.mkdtemp(prefix=f"pdf_{doc_id}_"))
    preset = _load_preset(template)

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
        "tables": [],
        "code_blocks": [],
        "callouts": [],
    }
    _docs[doc_id]["sections"].append(section)
    return {"section_id": section_id, "title": title}


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

    # Get natural dimensions
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

    for section in _docs[doc_id]["sections"]:
        if section["id"] == section_id:
            section["images"].append(img_data)
            return {"image_id": img_id, "filename": img_path.name}

    raise ValueError(f"Section {section_id} not found in document {doc_id}")


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

    for section in _docs[doc_id]["sections"]:
        if section["id"] == section_id:
            section["tables"].append(table_data)
            return {"table_id": table_id}

    raise ValueError(f"Section {section_id} not found")


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

    for section in _docs[doc_id]["sections"]:
        if section["id"] == section_id:
            section["code_blocks"].append(cb_data)
            return {"code_block_id": cb_id}

    raise ValueError(f"Section {section_id} not found")


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

    for section in _docs[doc_id]["sections"]:
        if section["id"] == section_id:
            section["callouts"].append(callout_data)
            return {"callout_id": callout_id}

    raise ValueError(f"Section {section_id} not found")


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
    """Compile the final PDF. Optionally specify output_path, otherwise saved next to the preview."""
    if doc_id not in _docs:
        raise ValueError(f"Document {doc_id} not found")

    pdf_path = _compile_typst(doc_id, output_format="pdf")

    if output_path:
        dest = Path(output_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pdf_path, dest)
        pdf_path = dest

    return {
        "pdf_path": str(pdf_path),
        "message": f"PDF ready: {pdf_path}",
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
