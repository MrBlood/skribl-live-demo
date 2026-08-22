"""Where things live, for suites that read the source tree directly.

Skribl's files moved when it became a blueprint: templates went from
templates/*.html to skribl/templates/skribl/*.html, and static assets from
static/skribl/* to skribl/static/*. The URLs did not change, so browser-driven
assertions were unaffected — but the handful of suites that read files off disk
were pinning the LAYOUT rather than the behaviour they meant to test.

This resolves either layout, so one harness runs against both trees and the
pre/post refactor comparison stays honest.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TEMPLATES_DIR = next(
    (p for p in (ROOT / "skribl" / "templates" / "skribl", ROOT / "templates")
     if p.is_dir()), ROOT / "templates")

STATIC_DIR = next(
    (p for p in (ROOT / "skribl" / "static", ROOT / "static" / "skribl")
     if p.is_dir()), ROOT / "static" / "skribl")


def template(name):
    return TEMPLATES_DIR / name


def vendored(name):
    """Path to a vendored library, or None if it is not in the tree."""
    p = STATIC_DIR / name
    return p if p.exists() else None
