# ::ILANG [TYPE:python-module][ROLE:source-constrained-seo]
# ::RULE{lastmod from verified meaningful change; schema fields from real source only}
# ::BOUNDARY{never:invent availability, expiry, reviews or price}
"""Structured-data and sitemap helpers with no runtime dependencies."""
from datetime import date, datetime
from decimal import Decimal
from html import escape
import json
from urllib.parse import urlparse

def jsonld(data):
    return '<script type="application/ld+json">' + json.dumps(
        data, ensure_ascii=False, separators=(",", ":")
    ).replace("</", "<\\/") + "</script>"

def breadcrumbs(base, items):
    return jsonld({
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i, "name": name, "item": base + "/" + path}
            for i, (name, path) in enumerate(items, 1)
        ],
    })

def itemlist(base, entries):
    return jsonld({
        "@context": "https://schema.org", "@type": "ItemList",
        "itemListElement": [
            {"@type": "ListItem", "position": i, "url": base + "/" + path}
            for i, path in enumerate(entries, 1)
        ],
    })

def valid_expiry(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        expiry = date.fromisoformat(value)
    except ValueError:
        return None
    return expiry.isoformat()

def expired(record, today=None):
    until = valid_expiry(record.get("valid_until"))
    return bool(until and date.fromisoformat(until) < (today or date.today()))

def valid_lastmod(value):
    if not isinstance(value, str):
        return None
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if stamp.tzinfo is None:
        return None
    return stamp.date().isoformat()

def sitemap_xml(base, paths, changed_at=None):
    if not base:
        return '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>'
    if any(not x.startswith("/") or "://" in x for x in paths):
        raise ValueError("Invalid sitemap path")
    changed_at = changed_at or {}
    rows = []
    for path in paths:
        stamp = valid_lastmod(changed_at.get(path))
        lastmod = f"<lastmod>{stamp}</lastmod>" if stamp else ""
        rows.append("<url><loc>" + escape(base + path, quote=True) + "</loc>" + lastmod + "</url>")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "\n".join(rows) + "\n</urlset>")