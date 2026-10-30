# VPS Deals — Official Pricing Radar

Independent, source-linked directory with **one deal page per verified VPS plan**. A deal here means a plan price listing—not a coupon or necessarily a discount. DigitalOcean Basic Regular Droplets are parsed from the official pricing table; Hetzner CPX/CCX models are parsed from Hetzner's public pricing JSON for HEL1 in USD. If a specific plan lacks a valid monthly price it is skipped. Prices include source URL, machine configuration, verification time and important billing conditions. Verify checkout prices, taxes, regional availability and extra IP charges with the provider.

## Quick start

```bash
python scraper.py
python build.py
python -m unittest discover -s tests
```

Static output: `site/`. Python 3.11+; no external Python dependencies.

## Cloudflare Pages

Use **Connect to Git** (production branch `main`), build command `python build.py`, build output `site`. The site URL must be copied from the actual Pages deployment. Update `domain` and `base_url` in `.ilang/site.ilang` to that exact URL, commit, rebuild, and verify `sitemap.xml` and `robots.txt`. Until a verified URL is present, the site intentionally disallows indexing to prevent emitting wrong canonical URLs.

## Update automation

`.github/workflows/update.yml` runs every six hours, checks official sources, builds and tests, then commits updated verified data. If *all* source prices fail, `scraper.py` raises an error **without overwriting the last verified data**; GitHub Actions reports a failed run, instead of deleting every deal. If just one source fails, its unverifiable plans are omitted from that successful refresh. A past verified price is not a guarantee of current availability; each deal shows its verification timestamp. Scheduled GitHub Actions runs may be delayed or disabled after prolonged inactivity; monitor failures.

## Compliance & monetization

Official source links only by default. A fourth provider field can hold an **approved** affiliate destination; do not fill it before checking each program's terms. A disclosure is always rendered. Affiliate links do not change the recorded source URL. Informational pricing directory, no warranty of availability.

Site rules are described using I-Lang; see `.ilang/site.ilang`; protocol notes: https://ilang.ai.