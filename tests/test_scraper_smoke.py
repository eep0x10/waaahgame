"""
Smoke test for scrape_unit_images module.
No network calls -- just verifies the module imports cleanly and
exposes the expected public API.
"""

import importlib
import sys
import os


def test_scraper_module_importable():
    """scrape_unit_images must import without errors."""
    # Ensure project root is on path (mirrors what the module itself does)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    mod = importlib.import_module('scripts.scrape_unit_images')
    assert mod is not None


def test_scraper_exposes_scrape_callable():
    """The scrape() function must be importable and callable."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from scripts.scrape_unit_images import scrape
    assert callable(scrape)


def test_scraper_exposes_selector_list():
    """WARSCROLL_IMG_SELECTORS must be a non-empty list of strings."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from scripts.scrape_unit_images import WARSCROLL_IMG_SELECTORS
    assert isinstance(WARSCROLL_IMG_SELECTORS, list)
    assert len(WARSCROLL_IMG_SELECTORS) > 0
    for sel in WARSCROLL_IMG_SELECTORS:
        assert isinstance(sel, str)
