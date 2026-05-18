"""Quick smoke test — generates a sample PDF without MCP."""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).parent.parent
TEMPLATES = ROOT / "templates"

doc = {
    "doc_id": "test",
    "title": "Тестовый документ",
    "author": "Author",
    "template": "report",
    "language": "ru",
    "font": "default",
    "sections": [
        {
            "id": "s1",
            "title": "Введение",
            "content": "Это тестовый раздел. *Курсив* и *жирный* текст работают. Здесь достаточно текста, чтобы проверить выравнивание по ширине и перенос строк на русском языке.",
            "level": 1,
            "numbered": True,
            "images": [],
            "tables": [],
            "code_blocks": [],
            "callouts": [],
        },
        {
            "id": "s2",
            "title": "Таблица и код",
            "content": "Пример раздела с таблицей и блоком кода.",
            "level": 1,
            "numbered": True,
            "images": [],
            "tables": [
                {
                    "id": "t1",
                    "headers": ["Инструмент", "Язык", "Звёзды"],
                    "rows": [["Typst", "Rust", "53K"], ["FastMCP", "Python", "25K"]],
                    "caption": "Используемые инструменты",
                }
            ],
            "code_blocks": [
                {
                    "id": "c1",
                    "code": 'mcp.tool()\ndef create_document(title: str) -> dict:\n    return {"doc_id": "abc"}',
                    "language": "python",
                    "caption": "Пример MCP-инструмента",
                }
            ],
            "callouts": [
                {"id": "co1", "text": "Это информационный блок — всё работает!", "kind": "tip"}
            ],
        },
    ],
}

work_dir = Path(tempfile.mkdtemp(prefix="pdf_test_"))
assets_dir = work_dir / "assets"
assets_dir.mkdir()

(assets_dir / "content.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

for f in TEMPLATES.glob("*.typ"):
    shutil.copy2(f, work_dir / f.name)

result = subprocess.run(
    ["typst", "compile", str(work_dir / "report.typ"), str(work_dir / "output.pdf")],
    capture_output=True, text=True, cwd=str(work_dir),
)

if result.returncode != 0:
    print("❌ Typst error:")
    print(result.stderr)
    sys.exit(1)

out = work_dir / "output.pdf"
dest = ROOT / "examples" / "test_output.pdf"
shutil.copy2(out, dest)
print(f"✅ PDF created: {dest}")
print(f"   Size: {dest.stat().st_size // 1024} KB")
