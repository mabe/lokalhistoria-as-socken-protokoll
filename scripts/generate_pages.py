#!/usr/bin/env python3
"""
Generate Jekyll markdown pages for Ås Socken protokoll
fetched from the SLHD (Swedish Local History Database) via JSONP.

Usage:
    python3 scripts/generate_pages.py

The script fetches records from the Lokalhistoria.nu API, then:
- Creates one markdown file per record in the _protokoll/ directory
- Creates/updates the index.md listing all protocols
"""

import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

API_URL = (
    "https://slhd.evryonehalmstad.se/Widget/Result"
    "?callback=CALLBACK"
    "&type=map"
    "&search_string="
    "&MapLocality=103"
    "&yearrange="
    "&from="
    "&to="
    "&county1=0"
    "&subjects="
    "&person_name="
    "&geo="
    "&url=http://www.lokalhistoria.nu/result_view"
    "&pagedResults=600"
    "&page=PAGE"
)

CALLBACK_NAME = "jsonpCallback"
REPO_ROOT = Path(__file__).parent.parent
PROTOCOLS_DIR = REPO_ROOT / "_protokoll"
INDEX_FILE = REPO_ROOT / "index.md"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; lokalhistoria-pages-generator/1.0)",
    "Accept": "text/javascript, application/javascript, */*",
    "Referer": "http://www.lokalhistoria.nu/",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def fetch_jsonp(page: int = 1) -> dict:
    """Fetch one page of results from the SLHD API and return parsed JSON."""
    url = API_URL.replace("CALLBACK", CALLBACK_NAME).replace("PAGE", str(page))
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.URLError as exc:
        print(f"[ERROR] Could not fetch page {page}: {exc}", file=sys.stderr)
        raise

    # Strip JSONP wrapper: CALLBACK_NAME(...)
    pattern = rf"^\s*{re.escape(CALLBACK_NAME)}\s*\((.*)\)\s*;?\s*$"
    match = re.match(pattern, raw, re.DOTALL)
    if not match:
        raise ValueError(f"Unexpected JSONP response format (page {page}): {raw[:200]}")
    return json.loads(match.group(1))


def slugify(text: str) -> str:
    """Convert text to a URL/filename-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[åä]", "a", text)
    text = re.sub(r"ö", "o", text)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text or "protokoll"


def safe_str(value) -> str:
    """Return a string, empty string for None/falsy."""
    if value is None:
        return ""
    return str(value).strip()


def extract_year(record: dict) -> str:
    """Try several common field names to get a year string."""
    for key in ("FromYear", "from_year", "Year", "year", "Date", "date"):
        val = record.get(key)
        if val:
            return safe_str(val)
    return ""


def extract_to_year(record: dict) -> str:
    """Try several common field names to get an end year string."""
    for key in ("ToYear", "to_year"):
        val = record.get(key)
        if val:
            return safe_str(val)
    return ""


def extract_title(record: dict) -> str:
    """Return the best available title string."""
    for key in ("Title", "title", "Name", "name"):
        val = record.get(key)
        if val:
            return safe_str(val)
    return "Okänd titel"


def extract_description(record: dict) -> str:
    """Return the best available description string."""
    for key in ("Description", "description", "Text", "text", "Content", "content"):
        val = record.get(key)
        if val:
            return safe_str(val)
    return ""


def extract_source_url(record: dict) -> str:
    """Return the URL to the original record on Lokalhistoria.nu."""
    for key in ("ResultUrl", "result_url", "Url", "url", "Link", "link"):
        val = record.get(key)
        if val:
            return safe_str(val)
    rec_id = safe_str(record.get("Id", record.get("id", "")))
    if rec_id:
        return f"http://www.lokalhistoria.nu/result_view/{rec_id}"
    return ""


def extract_thumbnail(record: dict) -> str:
    """Return a thumbnail URL if available."""
    for key in (
        "ThumbnailUrl",
        "thumbnail_url",
        "Thumbnail",
        "thumbnail",
        "ImageUrl",
        "image_url",
    ):
        val = record.get(key)
        if val:
            return safe_str(val)
    return ""


def extract_source(record: dict) -> str:
    """Return the archive/source name."""
    for key in ("Source", "source", "Archive", "archive", "Institution", "institution"):
        val = record.get(key)
        if val:
            return safe_str(val)
    return ""


def extract_record_type(record: dict) -> str:
    """Return the record type/category."""
    for key in ("Type", "type", "Category", "category", "RecordType", "record_type"):
        val = record.get(key)
        if val:
            return safe_str(val)
    return ""


def extract_records(data: dict) -> list:
    """Extract the list of records from the parsed JSONP payload."""
    for key in ("Result", "result", "Results", "results", "Items", "items", "Data", "data"):
        val = data.get(key)
        if isinstance(val, list):
            return val
    # Fallback: if the top-level itself is a list
    if isinstance(data, list):
        return data
    return []


def extract_total(data: dict) -> int:
    """Extract the total count of records from the payload."""
    for key in ("TotalCount", "total_count", "Total", "total", "Count", "count"):
        val = data.get(key)
        if val is not None:
            try:
                return int(val)
            except (TypeError, ValueError):
                pass
    return 0


# ---------------------------------------------------------------------------
# File writers
# ---------------------------------------------------------------------------


def yaml_escape(value: str) -> str:
    """Escape a value for use in YAML front-matter (double-quoted string)."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def write_protocol_page(record: dict, filename: str) -> Path:
    """Write one markdown file for a protocol record. Returns the path."""
    title = extract_title(record)
    year = extract_year(record)
    to_year = extract_to_year(record)
    description = extract_description(record)
    source_url = extract_source_url(record)
    thumbnail = extract_thumbnail(record)
    source = extract_source(record)
    record_type = extract_record_type(record)
    rec_id = safe_str(record.get("Id", record.get("id", "")))

    PROTOCOLS_DIR.mkdir(parents=True, exist_ok=True)
    filepath = PROTOCOLS_DIR / filename

    lines = ["---"]
    lines.append(f'title: "{yaml_escape(title)}"')
    if year:
        lines.append(f'year: "{yaml_escape(year)}"')
    if to_year:
        lines.append(f'to_year: "{yaml_escape(to_year)}"')
    if description:
        lines.append(f'description: "{yaml_escape(description)}"')
    if source_url:
        lines.append(f'source_url: "{yaml_escape(source_url)}"')
    if thumbnail:
        lines.append(f'thumbnail_url: "{yaml_escape(thumbnail)}"')
    if source:
        lines.append(f'source: "{yaml_escape(source)}"')
    if record_type:
        lines.append(f'record_type: "{yaml_escape(record_type)}"')
    if rec_id:
        lines.append(f'record_id: "{yaml_escape(rec_id)}"')
    lines.append("layout: protocol")
    lines.append("---")
    lines.append("")

    filepath.write_text("\n".join(lines), encoding="utf-8")
    return filepath


def write_index(records: list, generated_at: str) -> None:
    """Write the index.md file listing all protocols."""
    lines = [
        "---",
        'layout: default',
        f'title: "Protokoll – Ås Socken"',
        f'description: "Förteckning över {len(records)} protokoll från Ås Socken"',
        "---",
        "",
        "# Protokoll – Ås Socken",
        "",
        f"Förteckning med **{len(records)} protokoll** från Ås Socken, "
        f"hämtade från [Lokalhistoria.nu](http://www.lokalhistoria.nu/).",
        "",
        f"*Senast uppdaterad: {generated_at}*",
        "",
        '<div class="filter-bar">',
        '  <input type="text" id="protocolSearch" placeholder="Filtrera protokoll..." aria-label="Sök i protokoll">',
        "</div>",
        "",
        '<ul class="protocol-list" id="protocolList">',
    ]

    for rec in records:
        title = extract_title(rec)
        year = extract_year(rec)
        to_year = extract_to_year(rec)
        rec_id = safe_str(rec.get("Id", rec.get("id", "")))
        slug = _make_slug(rec)
        source = extract_source(rec)

        year_display = year
        if to_year and to_year != year:
            year_display = f"{year}–{to_year}"

        meta_parts = []
        if year_display:
            meta_parts.append(year_display)
        if source:
            meta_parts.append(source)
        meta_str = " | ".join(meta_parts)

        lines.append("  <li class=\"protocol-list-item\">")
        lines.append(f"    <a href=\"{{{{ site.baseurl }}}}/protokoll/{slug}/\">{title}</a>")
        if meta_str:
            lines.append(f"    <div class=\"protocol-list-meta\">{meta_str}</div>")
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
# Slug / filename helpers
# ---------------------------------------------------------------------------


def _make_slug(record: dict) -> str:
    """Build a deterministic, human-readable slug for a record."""
    rec_id = safe_str(record.get("Id", record.get("id", "")))
    title = extract_title(record)
    year = extract_year(record)

    # Prefer id-based slug to avoid collisions
    if rec_id:
        return f"{rec_id}"
    # Fall back to title + year slug
    base = slugify(f"{title}-{year}" if year else title)
    return base or "protokoll"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    force = os.environ.get("FORCE_REGENERATE", "false").lower() in ("1", "true", "yes")
    if force:
        print("[*] Force-regeneration enabled.")
    print("[*] Fetching protocols from Lokalhistoria.nu …")

    all_records = []
    page = 1
    while True:
        print(f"    Fetching page {page} …", end=" ", flush=True)
        try:
            data = fetch_jsonp(page)
        except Exception as exc:
            print(f"FAILED ({exc})")
            if page == 1:
                sys.exit(1)
            # Partial fetch – continue with what we have
            break

        records = extract_records(data)
        if not records:
            print("no records – done.")
            break

        all_records.extend(records)
        total = extract_total(data)
        print(f"got {len(records)} records (total so far: {len(all_records)}/{total or '?'})")

        if total and len(all_records) >= total:
            break

        page += 1
        time.sleep(0.5)  # Be polite to the server

    if not all_records:
        print("[WARN] No records fetched. Exiting without changes.", file=sys.stderr)
        sys.exit(0)

    print(f"[*] Processing {len(all_records)} records …")

    # Clean up old generated files
    if PROTOCOLS_DIR.exists():
        for old_file in PROTOCOLS_DIR.glob("*.md"):
            old_file.unlink()

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    seen_slugs: dict[str, int] = {}

    for rec in all_records:
        slug = _make_slug(rec)
        # Deduplicate slugs
        if slug in seen_slugs:
            seen_slugs[slug] += 1
            slug = f"{slug}-{seen_slugs[slug]}"
        else:
            seen_slugs[slug] = 0

        filename = f"{slug}.md"
        write_protocol_page(rec, filename)

    print(f"[OK] Created {len(all_records)} protocol pages in {PROTOCOLS_DIR}/")

    write_index(all_records, generated_at)
    print("[*] Done.")


if __name__ == "__main__":
    main()
