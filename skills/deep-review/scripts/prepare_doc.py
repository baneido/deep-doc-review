#!/usr/bin/env python3
"""Deep Review helper: convert a document to text and write a line-numbered copy.
usage: prepare_doc.py DOC RUN_DIR
writes RUN_DIR/doc.txt, RUN_DIR/doc.numbered.txt ("L0001| ..."), RUN_DIR/meta.json. Stdlib only;
PDF via pdftotext (poppler) / pypdf / macOS textutil fallback; DOCX via zipfile."""
import json, os, re, shutil, subprocess, sys, time, zipfile
from pathlib import Path


def pdf_text(p: Path) -> str:
    if shutil.which("pdftotext"):
        return subprocess.run(["pdftotext", "-layout", str(p), "-"], capture_output=True, text=True, check=True).stdout
    try:
        from pypdf import PdfReader  # type: ignore
        return "\n".join((pg.extract_text() or "") for pg in PdfReader(str(p)).pages)
    except ImportError:
        pass
    sys.exit("PDF needs pdftotext (brew install poppler) or pypdf (pip install pypdf). "
             "Alternatively extract the text yourself and pass a .txt file.")


def docx_text(p: Path) -> str:
    with zipfile.ZipFile(p) as z:
        xml = z.read("word/document.xml").decode("utf-8", "replace")
    xml = re.sub(r"</w:p>", "\n", xml)
    xml = re.sub(r"<w:tab/>", "\t", xml)
    txt = re.sub(r"<[^>]+>", "", xml)
    return re.sub(r"&lt;", "<", re.sub(r"&gt;", ">", re.sub(r"&amp;", "&", txt)))


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    doc, run = Path(sys.argv[1]).expanduser().resolve(), Path(sys.argv[2]).expanduser()
    run.mkdir(parents=True, exist_ok=True)
    (run / "passes").mkdir(exist_ok=True)
    ext = doc.suffix.lower()
    if ext == ".pdf":
        text = pdf_text(doc)
    elif ext == ".docx":
        text = docx_text(doc)
    elif ext in (".rtf", ".doc", ".pages") and shutil.which("textutil"):
        text = subprocess.run(["textutil", "-convert", "txt", "-stdout", str(doc)], capture_output=True, text=True, check=True).stdout
    else:
        text = doc.read_text(encoding="utf-8", errors="replace")
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\f", "\n")
    lines = text.split("\n")
    while lines and not lines[-1].strip():
        lines.pop()
    width = max(4, len(str(len(lines))))
    (run / "doc.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (run / "doc.numbered.txt").write_text(
        "\n".join(f"L{i:0{width}d}| {ln}" for i, ln in enumerate(lines, 1)) + "\n", encoding="utf-8")
    meta_p = run / "meta.json"
    meta = json.loads(meta_p.read_text()) if meta_p.exists() else {}
    meta.update({"source": str(doc), "lines": len(lines), "chars": len(text),
                 "approx_tokens": int(len(text) / (1.6 if re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", text) else 4)),
                 "numbered": str((run / "doc.numbered.txt").resolve())})
    meta.setdefault("started_at", time.time())
    meta_p.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()
