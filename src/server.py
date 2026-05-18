"""Beautiful PDF MCP — generates typographically clean PDFs via Typst.

AGENT WORKFLOW
--------------
1. create_document  — pick a template, get doc_id
2. add_section      — add sections with Markdown text (repeat as needed)
3. add_image / add_table / add_code_block / add_callout / add_gallery — enrich sections
4. compile_preview  — render page 1 as PNG, open it to verify layout
5. fix if needed    — update_section / remove_section
6. compile_pdf      — produce the final PDF, copy to destination
7. save_document    — ALWAYS save after compile so the user can reload later

TEMPLATE GUIDE
--------------
report       — business report / analytics. Navy accent, Source Serif 4 body,
               numbered headings, TOC, header+footer. Images centered by default;
               use position="right-wrap" / "left-wrap" for editorial wrap.
academic_ru  — Russian academic paper, GOST 7.32. PT Serif 14pt, 1.5× leading,
               wide left margin (30 mm), centered page numbers. ALL images are
               centered (GOST requirement, wrap is ignored). Callouts render
               without color. Supports #footnote[text] inline for real footnotes
               at the bottom of the page.
book         — long-form non-fiction. A5, Van de Graaf margins, PT Serif,
               chapter breaks, running headers.
technical    — API docs / developer guides. IBM Plex Sans, left-aligned text,
               numbered headings, syntax-highlighted code blocks.
portfolio    — visual showcase. Dark cover page, Noto Sans, violet accent,
               image-forward layout.
letter       — formal correspondence. DIN 5008 style, Source Sans 3,
               no page numbers, compact margins.
journal      — editorial / magazine. Images auto-wrap by default
               (even sections → right, odd → left). Golden beige accent.
               Use position="center" to force a standalone figure.

IMAGE POSITION VALUES
---------------------
center      — standalone centered figure (default, all templates)
right-wrap  — text wraps to the LEFT of the image (report/book/technical/portfolio/letter/journal)
left-wrap   — text wraps to the RIGHT of the image (same templates)
In academic_ru all images are centered regardless of position.

CALLOUT KINDS: info | warning | tip | danger | quote
In academic_ru callouts render as plain grey-bordered blocks (GOST: no color).

FOOTNOTES (academic_ru and all templates)
-----------------------------------------
Write #footnote[explanation text] inline in section content to get a proper
footnote number in the text and the note at the bottom of the page.
"""

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
    # Escape all # that are not part of #link() or #footnote[] we inserted
    text = re.sub(r"(?<!\\)#(?!link\(|footnote\[)", r"\\#", text)

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
    """Create a new document and return its doc_id. Always the first call.

    template choices:
      report      — business/analytics report (default)
      academic_ru — Russian academic paper, GOST 7.32 compliant
      book        — long-form non-fiction, A5
      technical   — API docs, developer guides
      portfolio   — visual showcase with dark cover
      letter      — formal correspondence
      journal     — editorial/magazine with auto image wrap

    language: "ru" or "en" — affects hyphenation and TOC heading language

    preset_overrides: override any typographic setting for this document only.
      Common uses:
        {"accent_color": "#2a9d8f"}          — custom brand colour (hex)
        {"show_toc": False}                  — disable table of contents
        {"body_font": "PT Serif"}            — override body font
        {"margin_left": "3.5cm"}             — wider left margin
        {"numbered_headings": False}         — remove heading numbers
      Full list of keys: accent_color, heading_color, muted_color, body_color,
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
    """Add a section to the document. Returns section_id needed for add_image etc.

    title: section heading text
    level: 1 = chapter/major section, 2 = subsection, 3 = minor subsection
    content: body text in Markdown.
      Supported: **bold**, *italic*, `inline code`, [link text](url)
      Academic footnotes: write #footnote[note text] inline — renders as
        a superscript number in the text and a footnote at the bottom of the page.
      For multi-paragraph content use \\n\\n between paragraphs.
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
    """Update the title or content of an existing section. Pass only the fields to change.

    Useful for fixing text after compile_preview reveals a problem.
    After updating, call compile_preview again to verify.
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

    path: absolute path to image file (PNG, JPG, SVG, PDF page)
    caption: figure caption shown below the image

    width: controls how wide the image is on the page
      "full"    = 100% of text width (default for large diagrams/charts)
      "large"   = 80%  (good default for most images)
      "half"    = 50%
      "third"   = 33%
      "quarter" = 25%
      Or pass an explicit percentage string: "65%"

    position: controls placement relative to surrounding text
      "center"     — standalone figure, full-width block (default, safe for all templates)
      "right-wrap" — image floats RIGHT, text wraps to the LEFT of it
      "left-wrap"  — image floats LEFT, text wraps to the RIGHT of it
      Note: wrap positions are ignored in academic_ru (GOST requires centered figures).
      For journal template, images wrap automatically even without setting position.
      Wrap works best with width 30–45% and a section with at least 3–4 lines of text.
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
    """Add a grid gallery of images to a section. Images are evenly distributed across columns.

    paths: list of absolute paths to image files (PNG, JPG, SVG) — 2 or more
    columns: 2 (default) | 3 | 4  — number of grid columns
    caption: optional caption for the whole gallery block

    Use add_gallery instead of multiple add_image calls when you have 2+ images
    that belong together: portfolio work samples, before/after comparisons,
    product photos, screenshot sets. The gallery is kept on one page (non-breaking).
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
    """Add a formatted table to a section.

    headers: list of column header strings, e.g. ["Region", "Revenue", "Growth"]
    rows: list of rows; each row is a list matching the number of headers,
          e.g. [["EMEA", "$4.2M", "+18%"], ["APAC", "$3.1M", "+31%"]]
    caption: optional table caption shown below

    Renders with alternating row shading and a bold header row.
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
    """Add a syntax-highlighted code block to a section.

    code: the code as a plain string (preserve indentation)
    language: syntax language for highlighting, e.g. "python", "typescript",
              "bash", "json", "sql", "rust", "go" — leave empty for plain text
    caption: optional label shown above the code (e.g. "main.py" or "API request")
    """
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
    """Add a highlighted callout box to a section.

    text: the callout text (Markdown supported)
    kind:
      info    — blue, ℹ  — for notes and supplementary information
      warning — orange, ⚠ — for cautions and important caveats
      tip     — green, ✓  — for best practices and recommendations
      danger  — red, ✗   — for critical warnings and breaking changes
      quote   — warm beige, ❝ — for pull quotes and highlighted statements

    In academic_ru all callouts render as plain grey-bordered blocks
    (no color — GOST 7.32 compliance).
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
    """Render the first page as a PNG and return its path. ALWAYS call before compile_pdf.

    Open the returned path to visually inspect the layout: check heading hierarchy,
    image placement, table widths, and overall spacing. Fix any issues with
    update_section or by adjusting image widths, then preview again before
    committing to the final PDF.
    """
    if doc_id not in _docs:
        raise ValueError(f"Document {doc_id} not found")

    out_path = _compile_typst(doc_id, output_format="png")
    return {
        "preview_path": str(out_path),
        "message": f"Preview saved to {out_path}. Open it to check layout.",
    }


@mcp.tool()
def compile_pdf(doc_id: str, output_path: str = "") -> dict:
    """Compile the final PDF and return its path.

    output_path: where to save the PDF, e.g. "~/Desktop/report.pdf"
                 If omitted, saved to a temp directory (path is returned).
                 Always specify output_path so the user can easily find the file.

    After compiling, call save_document to persist the document state —
    without it the document is lost if Claude Desktop restarts.
    """
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
    """Save the document state to a JSON file for persistence across restarts.

    path: where to save, e.g. "~/Desktop/my_report.json"

    Call this after every compile_pdf. If Claude Desktop restarts, the in-memory
    document is lost — use load_document(path) to restore it and continue editing.
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
    """Restore a document saved with save_document. Use after a Claude Desktop restart.

    path: path to the JSON file created by save_document
    Returns doc_id — use it with add_section, compile_pdf etc. to continue editing.
    Original image files must still exist at their original paths for compilation to work.
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
