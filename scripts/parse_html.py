#!/usr/bin/env python3
"""
Parse the Untitled-1.html file and generate Jekyll markdown pages
for all 511 Ås Socken protocol records.

Each <div> in the HTML contains:
  - An <a href="...">title</a> supplying the source URL and title
  - A <p>description</p> supplying the protocol summary

Usage:
    python3 scripts/parse_html.py [path/to/html_file]

Defaults to scripts/Untitled-1.html relative to the repo root.
"""

import html
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
DEFAULT_HTML_FILE = Path(__file__).parent / "Untitled-1.html"
PROTOCOLS_DIR = REPO_ROOT / "_protokoll"
INDEX_FILE = REPO_ROOT / "index.md"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def decode_js_unicode(text: str) -> str:
    """Decode JavaScript \\uXXXX escapes embedded in the HTML source."""
    return re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), text)


def yaml_escape(value: str) -> str:
    """Escape a value for use in YAML front-matter (double-quoted string)."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def extract_page_id(href: str) -> str:
    """Extract eoh_page_id from the URL, stripping the .xml extension."""
    m = re.search(r"eoh_page_id=([^&\s]+)", href)
    if m:
        return re.sub(r"\.xml$", "", m.group(1))
    return ""


def parse_records(content: str) -> list[dict]:
    """
    Parse the HTML content and return a list of record dicts with keys:
      title, source_url, description, slug
    """
    records = []
    # Each record is a <div> with exactly one <a> followed by one <p>
    div_re = re.compile(
        r"<div>\s*<a\s+href=\"([^\"]+)\">([^<]+)</a>\s*<p>(.*?)</p>\s*</div>",
        re.DOTALL,
    )
    for m in div_re.finditer(content):
        href = html.unescape(m.group(1).strip())
        title = html.unescape(m.group(2).strip())
        # Normalise internal whitespace in the description
        description = html.unescape(re.sub(r"\s+", " ", m.group(3).strip()))

        slug = extract_page_id(href)
        if not slug:
            # Fallback: derive slug from title
            slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "protokoll"

        records.append(
            {
                "title": title,
                "source_url": href,
                "description": description,
                "slug": slug,
            }
        )
    return records


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------


def write_protocol_page(record: dict) -> Path:
    """Write one markdown file for a protocol record and return its path."""
    PROTOCOLS_DIR.mkdir(parents=True, exist_ok=True)
    filepath = PROTOCOLS_DIR / f"{record['slug']}.md"

    lines = [
        "---",
        f'title: "{yaml_escape(record["title"])}"',
        f'source_url: "{yaml_escape(record["source_url"])}"',
        f'description: "{yaml_escape(record["description"])}"',
        "layout: protocol",
        "---",
        "",
    ]
    filepath.write_text("\n".join(lines), encoding="utf-8")
    return filepath


def write_index(records: list[dict]) -> None:
    """Write index.md listing all protocols."""
    lines = [
        "---",
        'layout: default',
        'title: "Protokoll – Ås Socken"',
        f'description: "Förteckning över {len(records)} protokoll från Ås Socken"',
        "---",
        "",
        "# Protokoll – Ås Socken",
        "",
        f"Förteckning med **{len(records)} protokoll** från Ås Socken, "
        f"hämtade från [Lokalhistoria.nu](http://www.lokalhistoria.nu/).",
        "",
        '<div class="filter-bar">',
        '  <input type="text" id="protocolSearch" '
        'placeholder="Filtrera protokoll..." aria-label="Sök i protokoll">',
        "</div>",
        "",
        '<ul class="protocol-list" id="protocolList">',
    ]

    for rec in records:
        lines.append('  <li class="protocol-list-item">')
        lines.append(
            f'    <a href="{{{{ site.baseurl }}}}/protokoll/{rec["slug"]}/">'
            f'{rec["title"]}</a>'
        )
        lines.append("  </li>")

    lines += [
        "</ul>",
        "",
        "<script>",
        "  var input = document.getElementById('protocolSearch');",
        "  var items = document.querySelectorAll('.protocol-list-item');",
        "  input.addEventListener('input', function() {",
        "    var filter = this.value.toLowerCase();",
        "    items.forEach(function(item) {",
        "      var text = item.textContent.toLowerCase();",
        "      item.style.display = text.indexOf(filter) > -1 ? '' : 'none';",
        "    });",
        "  });",
        "</script>",
        "",
    ]

    INDEX_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Wrote {INDEX_FILE}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    html_file = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_HTML_FILE

    if not html_file.exists():
        print(f"[ERROR] HTML file not found: {html_file}", file=sys.stderr)
        sys.exit(1)

    print(f"[*] Reading {html_file} …")
    raw = html_file.read_text(encoding="utf-8")

    # The file uses JavaScript \\uXXXX escapes – decode them first
    content = decode_js_unicode(raw)

    print("[*] Parsing records …")
    records = parse_records(content)
    print(f"[*] Found {len(records)} records.")

    if not records:
        print("[WARN] No records found. Exiting.", file=sys.stderr)
        sys.exit(1)

    # Remove old generated files
    if PROTOCOLS_DIR.exists():
        old_files = list(PROTOCOLS_DIR.glob("*.md"))
        for f in old_files:
            f.unlink()
        if old_files:
            print(f"[*] Removed {len(old_files)} old file(s) from {PROTOCOLS_DIR}/")

    # Deduplicate slugs
    seen: dict[str, int] = {}
    for rec in records:
        slug = rec["slug"]
        if slug in seen:
            seen[slug] += 1
            rec["slug"] = f"{slug}-{seen[slug]}"
        else:
            seen[slug] = 0

    print(f"[*] Writing markdown files to {PROTOCOLS_DIR}/ …")
    for rec in records:
        write_protocol_page(rec)

    print(f"[OK] Created {len(records)} protocol pages in {PROTOCOLS_DIR}/")

    write_index(records)
    print("[*] Done.")


if __name__ == "__main__":
    main()
