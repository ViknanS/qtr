"""End-to-end checks of the GitHub Pages site in a headless browser.

Serves ``docs/`` under the same ``/qtr/`` base path GitHub Pages uses and
drives it with Playwright. Skipped unless Playwright and a Chromium build are
installed (``pip install playwright && playwright install chromium``).
"""

import contextlib
import functools
import http.server
import pathlib
import re
import socketserver
import threading

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
pytestmark = pytest.mark.integration


class _Handler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        # Map /qtr/... -> docs/... ; anything else is a 404 like on Pages.
        path = path.split("?", 1)[0].split("#", 1)[0]
        if not path.startswith("/qtr/") and path != "/qtr":
            return str(DOCS / "__not_found__")
        rel = path[len("/qtr"):].lstrip("/") or "index.html"
        return str(DOCS / rel)

    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def base_url():
    handler = functools.partial(_Handler, directory=str(DOCS))
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as httpd:
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        yield f"http://127.0.0.1:{httpd.server_address[1]}/qtr/"
        httpd.shutdown()


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception as exc:  # browser binary missing
            pytest.skip(f"Chromium not available: {exc}")
        yield b
        b.close()


@contextlib.contextmanager
def page(browser, base_url, width=1366, scheme="dark"):
    ctx = browser.new_context(viewport={"width": width, "height": 900}, color_scheme=scheme)
    ctx.grant_permissions(["clipboard-read", "clipboard-write"])
    pg = ctx.new_page()
    problems = []
    pg.on("pageerror", lambda e: problems.append(f"pageerror: {e}"))
    pg.on("console", lambda m: problems.append(f"console.{m.type}: {m.text}") if m.type in ("error", "warning") else None)
    pg.on("requestfailed", lambda r: problems.append(f"requestfailed: {r.url}"))
    pg.on("response", lambda r: problems.append(f"HTTP {r.status}: {r.url}") if r.status >= 400 else None)
    pg.goto(base_url, wait_until="networkidle")
    try:
        yield pg, problems
    finally:
        ctx.close()


def test_loads_without_errors_and_assets_resolve(browser, base_url):
    with page(browser, base_url) as (pg, problems):
        pg.wait_for_timeout(500)
        assert pg.title().startswith("qqr")
        assert problems == []
        # every same-site asset referenced by the page is reachable under /qtr/
        urls = pg.eval_on_selector_all(
            "link[href], script[src], img[src]", "els => els.map(e => e.href || e.src)"
        )
        local = [u for u in urls if u.startswith(base_url)]
        assert local, "no local assets found"
        for u in local:
            assert pg.request.get(u).status == 200, u


def test_internal_links_point_to_existing_sections(browser, base_url):
    with page(browser, base_url) as (pg, _):
        hrefs = pg.eval_on_selector_all("a[href^='#']", "els => els.map(e => e.getAttribute('href'))")
        ids = set(pg.eval_on_selector_all("[id]", "els => els.map(e => e.id)"))
        missing = sorted({h for h in hrefs if h[1:] not in ids})
        assert not missing
        # no relative links that would escape the /qtr/ base path
        rel = pg.eval_on_selector_all("a[href]", "els => els.map(e => e.getAttribute('href'))")
        assert not [h for h in rel if h.startswith("/")]


def test_simulator_every_topology(browser, base_url):
    expected_calls = {"anchor": "7", "round_robin": "28", "swiss": "12", "single_elimination": "14"}
    with page(browser, base_url) as (pg, problems):
        for method in ["anchor", "round_robin", "swiss", "double_elimination", "single_elimination"]:
            pg.click(f"#method-seg button[data-method='{method}']")
            assert pg.locator("#standings tbody tr").count() == 8
            if method in expected_calls:
                assert pg.inner_text("#kpi-calls") == expected_calls[method]
            pg.click("#tab-matches")
            assert pg.locator("#panel-matches").is_visible()
            assert pg.locator("#panel-matches .m, #panel-matches .matrix").count() > 0
            pg.click("#tab-standings")
        # random data, group size 13, noisy judge
        pg.click("#data-seg button[data-data='random']")
        pg.fill("#group-size", "13")
        pg.dispatch_event("#group-size", "input")
        pg.fill("#noise", "1.5")
        pg.dispatch_event("#noise", "input")
        assert pg.locator("#standings tbody tr").count() == 13
        assert pg.inner_text("#noise-out") == "1.5"
        # invalid seed is clamped instead of breaking the run
        pg.fill("#seed", "-5")
        pg.dispatch_event("#seed", "change")
        assert pg.input_value("#seed") == "0"
        pg.click("#run-btn")
        assert pg.locator("#toast.show").count() == 1
        # compare tab
        pg.click("#tab-compare")
        pg.click("#compare-btn")
        assert pg.locator("#compare-out tbody tr").count() == 5
        assert problems == []


def test_workflow_architecture_theme_and_copy(browser, base_url):
    with page(browser, base_url, scheme="light") as (pg, problems):
        for flow in ["arise", "rti", "arena"]:
            pg.click(f"#flow-tabs [data-flow='{flow}']")
            assert pg.locator("#flow-steps li").count() == 5
        pg.click("#flow-detail button[data-go='1']")
        assert pg.get_attribute("#flow-steps button[data-i='1']", "aria-current") == "step"

        pg.click(".arch .node[data-node='mcp']")
        assert "MCP layer" in pg.inner_text("#arch-info")

        pg.click("#theme-toggle")
        assert pg.get_attribute("html", "data-theme") == "dark"
        pg.reload(wait_until="networkidle")
        assert pg.get_attribute("html", "data-theme") == "dark"  # persisted

        pg.click("#install .copy >> nth=0")
        assert "git clone" in pg.evaluate("navigator.clipboard.readText()")
        pg.click("#papers-list button[data-bib='0']")
        assert "2601.06487" in pg.evaluate("navigator.clipboard.readText()")
        assert problems == []


@pytest.mark.parametrize("width", [360, 390, 768, 1024])
def test_responsive_no_horizontal_scroll(browser, base_url, width):
    with page(browser, base_url, width=width) as (pg, problems):
        overflow = pg.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        assert overflow <= 0, f"{overflow}px horizontal overflow at {width}px"
        if width < 980:
            assert pg.locator("#nav-links").is_hidden()
            pg.click("#menu-btn")
            assert pg.locator("#nav-links").is_visible()
            pg.click("#nav-links a[href='#benchmarks']")
            assert pg.locator("#nav-links").is_hidden()
            # smooth scrolling: wait until the section settles under the sticky nav
            pg.wait_for_function(
                "Math.abs(document.getElementById('benchmarks').getBoundingClientRect().top) < 120",
                timeout=5000,
            )
        assert problems == []


def test_404_page(browser, base_url):
    with page(browser, base_url) as (pg, _):
        resp = pg.goto(base_url + "404.html")
        assert resp.status == 200
        assert re.search(r"qqr", pg.title())
        href = pg.get_attribute("a.btn-primary", "href")
        assert href and not href.startswith("/") or href == "/qtr/"
