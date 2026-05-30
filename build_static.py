"""Build a static GitHub Pages version of ProcessInsight.

GitHub Pages serves static files only. This exporter renders the public/demo
pages with Flask, copies assets, and injects a small notice for backend-only
actions such as login, registration, simulations, history, and AI calls.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / os.environ.get("STATIC_OUTPUT_DIR", "site")
BASE_PATH = "/" + os.environ.get("GITHUB_PAGES_BASE_PATH", "").strip("/")
if BASE_PATH == "/":
    BASE_PATH = ""

PAGES = [
    ("/", "index.html"),
    ("/select", "select/index.html"),
    (
        "/config?process=distillation&process=flash&process=absorption&process=extraction&process=pump&process=compressor&process=heat_exchanger",
        "config/index.html",
    ),
]

def rewrite_paths(html: str) -> str:
    """Prefix root-relative generated URLs with the GitHub Pages base path."""
    if BASE_PATH:
        for attr in ("href", "src", "action"):
            html = html.replace(f'{attr}="/', f'{attr}="{BASE_PATH}/')
        html = html.replace("fetch('/", f"fetch('{BASE_PATH}/")
        html = html.replace('fetch("/', f'fetch("{BASE_PATH}/')
    return html

def write_page(relative_path: str, content: str) -> None:
    target = OUTPUT_DIR / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")

def copy_static_assets() -> None:
    source = ROOT / "static"
    destination = OUTPUT_DIR / "static"
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)
    (OUTPUT_DIR / ".nojekyll").write_text("", encoding="utf-8")

def build() -> None:
    os.environ.setdefault("SECRET_KEY", "static-build-secret")

    from app import app

    app.config.update(
        LOGIN_DISABLED=True,
        SERVER_NAME="localhost",
        PREFERRED_URL_SCHEME="https",
    )

    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True)

    with app.test_client() as client:
        for route, output in PAGES:
            response = client.get(route, follow_redirects=True)
            if response.status_code >= 400:
                raise RuntimeError(
                    f"Static export failed for {route}: HTTP {response.status_code}"
                )
            write_page(output, rewrite_paths(response.get_data(as_text=True)))

    copy_static_assets()
    print(f"Static site generated in {OUTPUT_DIR}")

if __name__ == "__main__":
    build()
