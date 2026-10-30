# VPS Deals — Official Pricing Radar

A **VPS deal** is published **only when the provider shows a regular price and a lower promotional price for the same plan on the same official page**, together with clear offer terms. List prices, free signup credits, coupon speculation and marketing headlines without comparable per-plan prices do not become deals. Hostinger and IONOS are monitored for explicit price reductions; DigitalOcean and Hetzner are monitored but show no deals unless an official matched discount source is added. Vultr and Linode have been replaced after their earlier official pricing pages were unavailable for compliant automated checks. One deal page is generated per verified discount; when no deals qualify, the sitemap includes only the homepage, four provider pages, and comparison page.

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

`.github/workflows/update.yml` runs every six hours, checks official sources, builds and tests, then commits updated verified data. A refresh with zero qualifying discounts is **valid**: it replaces stale deals with an empty list. An inaccessible provider cannot retain old deals, and standard list prices are always excluded. A deal carries the source URL, last verification timestamp, original and introductory price, savings amount, commitment and renewal note. GitHub Actions reports failures separately if the code crashes; schedule delays are possible. Scheduled GitHub Actions runs may be delayed or disabled after prolonged inactivity; monitor failures.

## Retired list-price pages

The prior 20 plain-list-price pages are removed from the sitemap. `data/retired_deals.json` records their exact historic slugs. Each build emits a permanent 301 from those URLs to the corresponding provider overview in `site/_redirects`, and a custom noindex `404.html` prevents unknown URLs being treated as the homepage. No historic list price is eligible for deal structured data.

## Compliance & monetization

Official source links only by default. A fourth provider field can hold an **approved** affiliate destination; do not fill it before checking each program's terms. A disclosure is always rendered. Affiliate links do not change the recorded source URL. Informational pricing directory, no warranty of availability.

Site rules are described using I-Lang; see `.ilang/site.ilang`; protocol notes: https://ilang.ai.