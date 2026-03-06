"""Playwright browser tests for the TeXFrog HTML viewer.

These tests exercise the interactive JavaScript UI (sidebar navigation,
keyboard shortcuts, zoom, help overlay, responsive layout, game panel
display) against a synthetic HTML site that requires no pdflatex or
other system tools.

Skipped automatically when Playwright browsers are not installed.
"""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import expect

from tests.conftest import GAMES_DATA, needs_playwright

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NUM_GAMES = len(GAMES_DATA)


def _wait_for_game(page, label: str):
    """Wait until the viewer has navigated to the given game label."""
    page.wait_for_function(
        f"window.location.hash === '#{label}'"
    )


# ---------------------------------------------------------------------------
# A. Page Load & Initial State
# ---------------------------------------------------------------------------


@needs_playwright
def test_page_title(page, html_server):
    page.goto(html_server)
    assert page.title() == "TeXFrog Proof Viewer"


@needs_playwright
def test_initial_game_selected(page, html_server):
    page.goto(html_server)
    _wait_for_game(page, "G0")
    # First sidebar item is active
    first_li = page.locator("#game-list li").nth(0)
    expect(first_li).to_have_class(re.compile(r"active"))
    # Hash is set to first game
    assert page.evaluate("window.location.hash") == "#G0"


@needs_playwright
def test_sidebar_populated(page, html_server):
    page.goto(html_server)
    items = page.locator("#game-list li")
    expect(items).to_have_count(NUM_GAMES)
    # Each item has label and description divs
    for i in range(NUM_GAMES):
        li = items.nth(i)
        assert li.locator(".game-label").count() == 1
        assert li.locator(".game-desc").count() == 1


# ---------------------------------------------------------------------------
# B. Sidebar Navigation
# ---------------------------------------------------------------------------


@needs_playwright
def test_click_sidebar_selects_game(page, html_server):
    page.goto(html_server)
    _wait_for_game(page, "G0")
    items = page.locator("#game-list li")
    # Click the 4th item (G2, index 3)
    items.nth(3).click()
    _wait_for_game(page, "G2")
    expect(items.nth(3)).to_have_class(re.compile(r"active"))


@needs_playwright
def test_active_class_exclusive(page, html_server):
    page.goto(html_server)
    _wait_for_game(page, "G0")
    items = page.locator("#game-list li")
    items.nth(1).click()
    _wait_for_game(page, "G1")
    expect(page.locator("#game-list li.active")).to_have_count(1)
    items.nth(3).click()
    _wait_for_game(page, "G2")
    expect(page.locator("#game-list li.active")).to_have_count(1)


@needs_playwright
def test_prev_next_buttons(page, html_server):
    page.goto(html_server)
    _wait_for_game(page, "G0")
    page.click("#btn-next")
    _wait_for_game(page, "G1")
    page.click("#btn-prev")
    _wait_for_game(page, "G0")


# ---------------------------------------------------------------------------
# C. Keyboard Navigation
# ---------------------------------------------------------------------------


@needs_playwright
def test_arrow_right(page, html_server):
    page.goto(html_server)
    _wait_for_game(page, "G0")
    page.keyboard.press("ArrowRight")
    _wait_for_game(page, "G1")


@needs_playwright
def test_arrow_left(page, html_server):
    page.goto(html_server)
    _wait_for_game(page, "G0")
    page.keyboard.press("ArrowRight")
    _wait_for_game(page, "G1")
    page.keyboard.press("ArrowLeft")
    _wait_for_game(page, "G0")


@needs_playwright
def test_arrow_boundary(page, html_server):
    page.goto(html_server)
    _wait_for_game(page, "G0")
    # ArrowLeft on first game stays at G0
    page.keyboard.press("ArrowLeft")
    assert page.evaluate("window.location.hash") == "#G0"
    # Navigate to last game by clicking through
    last_idx = len(GAMES_DATA) - 1
    last_label = GAMES_DATA[-1]["label"]
    page.evaluate(f"showGame({last_idx})")
    _wait_for_game(page, last_label)
    page.keyboard.press("ArrowRight")
    assert page.evaluate("window.location.hash") == f"#{last_label}"


# ---------------------------------------------------------------------------
# D. URL Hash Navigation
# ---------------------------------------------------------------------------


@needs_playwright
def test_load_with_hash(page, html_server):
    page.goto(f"{html_server}#G2")
    _wait_for_game(page, "G2")
    # G2 should be the active game (4th item, index 3)
    active = page.locator("#game-list li.active")
    expect(active).to_have_count(1)
    # Verify by checking the hash directly
    assert page.evaluate("window.location.hash") == "#G2"


@needs_playwright
def test_hash_updates(page, html_server):
    page.goto(html_server)
    _wait_for_game(page, "G0")
    page.keyboard.press("ArrowRight")
    _wait_for_game(page, "G1")
    page.keyboard.press("ArrowRight")
    _wait_for_game(page, "Red1")


@needs_playwright
def test_invalid_hash_fallback(page, html_server):
    page.goto(f"{html_server}#NONEXISTENT")
    # Falls back to first game
    _wait_for_game(page, "G0")


# ---------------------------------------------------------------------------
# E. Zoom Controls
# ---------------------------------------------------------------------------


@needs_playwright
def test_zoom_in_button(page, html_server):
    page.goto(html_server)
    _wait_for_game(page, "G0")
    page.locator("#zoom-controls button", has_text="+").click()
    expect(page.locator("#zoom-level")).to_have_text("110%")


@needs_playwright
def test_zoom_out_button(page, html_server):
    page.goto(html_server)
    _wait_for_game(page, "G0")
    page.locator("#zoom-controls button:first-child").click()
    expect(page.locator("#zoom-level")).to_have_text("90%")


@needs_playwright
def test_zoom_keyboard(page, html_server):
    page.goto(html_server)
    _wait_for_game(page, "G0")
    page.keyboard.press("+")
    expect(page.locator("#zoom-level")).to_have_text("110%")
    page.keyboard.press("-")
    expect(page.locator("#zoom-level")).to_have_text("100%")
    # Test clamping at minimum (50%)
    for _ in range(10):
        page.keyboard.press("-")
    expect(page.locator("#zoom-level")).to_have_text("50%")
    # Test clamping at maximum (200%)
    for _ in range(20):
        page.keyboard.press("+")
    expect(page.locator("#zoom-level")).to_have_text("200%")


# ---------------------------------------------------------------------------
# F. Help Overlay
# ---------------------------------------------------------------------------


@needs_playwright
def test_help_button(page, html_server):
    page.goto(html_server)
    overlay = page.locator("#help-overlay")
    page.click("#help-btn")
    expect(overlay).to_have_class(re.compile(r"visible"))


@needs_playwright
def test_question_mark_toggle(page, html_server):
    page.goto(html_server)
    overlay = page.locator("#help-overlay")
    page.keyboard.press("?")
    expect(overlay).to_have_class(re.compile(r"visible"))
    page.keyboard.press("?")
    expect(overlay).not_to_have_class(re.compile(r"visible"))


@needs_playwright
def test_escape_closes_help(page, html_server):
    page.goto(html_server)
    overlay = page.locator("#help-overlay")
    page.keyboard.press("?")
    expect(overlay).to_have_class(re.compile(r"visible"))
    page.keyboard.press("Escape")
    expect(overlay).not_to_have_class(re.compile(r"visible"))


# ---------------------------------------------------------------------------
# G. Game Panel Display
# ---------------------------------------------------------------------------


@needs_playwright
def test_first_game_single_panel(page, html_server):
    page.goto(html_server)
    _wait_for_game(page, "G0")
    panels = page.locator("#game-svg-container .game-panel")
    expect(panels).to_have_count(1)


@needs_playwright
def test_regular_game_two_panels(page, html_server):
    """G1 is a regular non-first game: shows G0-removed + G1 side-by-side."""
    page.goto(f"{html_server}#G1")
    _wait_for_game(page, "G1")
    panels = page.locator("#game-svg-container .game-panel")
    expect(panels).to_have_count(2)


@needs_playwright
def test_reduction_three_panels(page, html_server):
    """Red1 is a reduction with 2 related_games: shows 3 panels."""
    page.goto(f"{html_server}#Red1")
    _wait_for_game(page, "Red1")
    panels = page.locator("#game-svg-container .game-panel")
    expect(panels).to_have_count(3)


@needs_playwright
def test_commentary_shown(page, html_server):
    """G1 has has_commentary=True: commentary-box should contain an img."""
    page.goto(f"{html_server}#G1")
    _wait_for_game(page, "G1")
    expect(page.locator("#commentary-box img")).to_have_count(1)


@needs_playwright
def test_no_commentary(page, html_server):
    """G0 has has_commentary=False: commentary-box should be empty."""
    page.goto(html_server)
    _wait_for_game(page, "G0")
    expect(page.locator("#commentary-box img")).to_have_count(0)


# ---------------------------------------------------------------------------
# H. Responsive Layout
# ---------------------------------------------------------------------------


@needs_playwright
def test_mobile_hamburger_visible(page, html_server):
    page.set_viewport_size({"width": 600, "height": 800})
    page.goto(html_server)
    expect(page.locator("#nav-toggle")).to_be_visible()


@needs_playwright
def test_mobile_sidebar_toggle(page, html_server):
    page.set_viewport_size({"width": 600, "height": 800})
    page.goto(html_server)
    nav = page.locator("#nav")
    # Open sidebar
    page.click("#nav-toggle")
    expect(nav).to_have_class(re.compile(r"open"))
    # Close via backdrop
    page.click("#nav-backdrop", force=True)
    expect(nav).not_to_have_class(re.compile(r"open"))


@needs_playwright
def test_medium_width_sidebar_no_descriptions(page, html_server):
    """At medium width, sidebar is visible but game descriptions are hidden."""
    page.set_viewport_size({"width": 900, "height": 800})
    page.goto(html_server)
    _wait_for_game(page, "G0")
    # Sidebar visible, hamburger hidden
    expect(page.locator("#nav")).to_be_visible()
    expect(page.locator("#nav-toggle")).not_to_be_visible()
    # Game labels visible, descriptions hidden
    expect(page.locator("#game-list .game-label").first).to_be_visible()
    expect(page.locator("#game-list .game-desc").first).not_to_be_visible()


@needs_playwright
def test_desktop_no_hamburger(page, html_server):
    page.set_viewport_size({"width": 1200, "height": 800})
    page.goto(html_server)
    expect(page.locator("#nav-toggle")).not_to_be_visible()


# ---------------------------------------------------------------------------
# I. Button State
# ---------------------------------------------------------------------------


@needs_playwright
def test_prev_disabled_first_game(page, html_server):
    page.goto(html_server)
    _wait_for_game(page, "G0")
    expect(page.locator("#btn-prev")).to_be_disabled()
    expect(page.locator("#btn-next")).not_to_be_disabled()


@needs_playwright
def test_next_disabled_last_game(page, html_server):
    last_label = GAMES_DATA[-1]["label"]
    page.goto(f"{html_server}#{last_label}")
    _wait_for_game(page, last_label)
    expect(page.locator("#btn-next")).to_be_disabled()
    expect(page.locator("#btn-prev")).not_to_be_disabled()
