# ::ILANG [TYPE:python-module][ROLE:front-end-status-copy]
# ::RULE{all internal crawl states map to user-readable English}
# ::BOUNDARY{never:render raw internal state codes}
"""Explicit exhaustive public state copy; unknown values use a safe fallback."""
STATUS_COPY = {
    "verified_discounts": "Current discounts have been checked against the provider's official pricing.",
    "standard_prices_verified": "Current standard plan prices have been checked against the official pricing page.",
    "no_verified_discount": "No qualifying discount is currently verified.",
    "parser_not_implemented": "Plan-level prices have not yet been independently checked.",
    "robots_blocked": "Automated verification is not available for this source.",
    "fetch_failed": "The official pricing page could not be checked recently.",
    "not_checked": "The official pricing page has not yet been checked.",
    "scraper_error": "The latest source verification was unsuccessful.",
    "no_deal": "No qualifying discount is currently verified.",
}
FALLBACK = "Price verification is currently unavailable; check the provider directly."

def public_status(value):
    return STATUS_COPY.get(value, FALLBACK)