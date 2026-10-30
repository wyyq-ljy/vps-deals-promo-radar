# VPS Deals — Official Pricing Radar

Independent, source-linked directory of VPS providers. Updated by a deterministic Python workflow. **Not all public prices are promotions.** Prices are omitted unless the parser can verify an explicit current price and plan on an official page. Verify billing terms with the provider before purchasing.

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

`.github/workflows/update.yml` runs every six hours, checks sources conservatively, builds and tests, then commits updated verified data only when changed. GitHub may delay scheduled runs, and inactive public repositories may have scheduled workflows disabled after 60 days without repository activity. Monitor workflow failures. Source fetch failures do not become invented offers.

## Compliance & monetization

Official source links only by default. A fourth provider field can hold an **approved** affiliate destination; do not fill it before checking each program's terms. A disclosure is always rendered. Affiliate links do not change the recorded source URL. Informational pricing directory, no warranty of availability.

Site rules are described using I-Lang; see `.ilang/site.ilang`; protocol notes: https://ilang.ai.