"""Generate standalone HTML documentation using the standard library."""
from pathlib import Path
import ast
import hashlib
import html

ROOT = Path(__file__).resolve().parents[1]


def signature(node):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        args = ast.unparse(node.args)
        result = f"{node.name}({args})"
        if node.returns:
            result += " -> " + ast.unparse(node.returns)
        return result
    return node.name


def build():
    source_path = ROOT / "payment.py"
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    guide = (ROOT / "docs" / "guide.txt").read_text(encoding="utf-8")
    elements = []
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            elements.append("<h2><code>" + html.escape(signature(node)) + "</code></h2>")
            doc = ast.get_docstring(node)
            if doc:
                elements.append("<p>" + html.escape(doc) + "</p>")
            if isinstance(node, ast.ClassDef):
                for method in node.body:
                    if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        elements.append("<h3><code>" + html.escape(signature(method)) + "</code></h3>")
                        doc = ast.get_docstring(method)
                        if doc:
                            elements.append("<p>" + html.escape(doc) + "</p>")
    body = "\n".join(elements)
    page = f"""<!doctype html>
<html lang="ru"><meta charset="utf-8"><title>Система оплаты версия {html.escape(version)}</title>
<style>body{{font:18px/1.5 Georgia,serif;max-width:950px;margin:40px auto;padding:0 24px;color:#111}}
code,pre{{font:15px/1.5 monospace;white-space:pre-wrap;overflow-wrap:anywhere}}
h1,h2,h3{{line-height:1.25}}pre{{background:#f4f4f4;padding:16px}}</style>
<h1>Система оплаты интернет-магазина</h1><p>Версия {html.escape(version)}</p>
<h2>Руководство</h2><pre>{html.escape(guide)}</pre>
<h2>Контрольная сумма payment.py</h2><pre>{source_hash}</pre>
<h2>Интерфейс модуля</h2>{body}</html>"""
    target = ROOT / "build" / "docs" / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(page, encoding="utf-8")
    print("Documentation: build/docs/index.html")
    print("API sections:", len(elements))
    print("Source SHA256:", source_hash)
    print("HTML SHA256:", hashlib.sha256(target.read_bytes()).hexdigest())
    return target


if __name__ == "__main__":
    build()
