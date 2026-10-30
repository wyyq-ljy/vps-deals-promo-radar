# VPS Deals — Verified VPS Discounts

**Live site:** https://vps.madebyyong.com/ · **Source:** https://github.com/wyyq-ljy/vps-deals-promo-radar

A **VPS deal** is published **only when the provider shows a regular price and a lower promotional price for the same plan on the same official page**, together with clear offer terms. List prices, free signup credits, coupon speculation and marketing headlines without comparable per-plan prices do not become deals. The first verified discount parsers cover Hostinger, IONOS, DreamHost, InMotion Hosting, Ultahost and HostArmada. Other official providers are present in the I-Lang monitored-source directory but are explicitly marked `parser_not_implemented` until a source-specific extraction is reviewed. A reachable official page is not proof that it has no promotion. No plan without a validated price difference is indexed as a deal. A provider page is indexable only when it has one or more verified discounts **or** at least three independently verified named configurations with USD list prices, specs, official source and verification timestamp. Providers with insufficient evidence stay monitored in `.ilang/site.ilang` but are excluded from site navigation and sitemap; their former URLs are not published. When no qualifying deals exist, the sitemap retains the homepage, comparison and only independently verified standard-rate provider pages.

## Quick start

```bash
python scraper.py
python build.py
python -m unittest discover -s tests
```

Static output: `site/`. Python 3.11+; no external Python dependencies.

## Cloudflare Pages

Already connected to GitHub `main`. Build command: `python build.py`; output directory: `site/`. Production canonical and sitemap are **https://vps.madebyyong.com/**. The `pages.dev` deployment is only the fallback/testing address. When changing domains, update *both* `domain` and `base_url` in `.ilang/site.ilang` and verify every sitemap and canonical URL after deployment. Never synthesize a Pages hostname from the project name. Output is deterministic and uses no runtime inference, credentials or paid APIs.

## Update automation

`.github/workflows/update.yml` runs every six hours, checks official sources, builds and tests, then commits updated verified data. A refresh with zero qualifying discounts is **valid**: it replaces stale deals with an empty list (the sitemap then has only the homepage, comparison and evidence-backed standard-rate provider URLs). An inaccessible provider cannot retain old deals. A deal carries its official source, last verification timestamp, actual original/promotional price difference, commitment and renewal note. `last_changed_at` is retained across unchanged price checks; the sitemap emits `lastmod` on deal URLs only from that meaningful change time, not from each cron execution. Schedules can be delayed or disabled after prolonged inactivity; check Actions and Cloudflare deployment logs.

## Thin-page policy

DigitalOcean (31 separately identified configurations), Hetzner (6 named CCX plans and US-HIL1 USD prices cross-checked against official JSON), Cloudways (11 managed DigitalOcean Standard sizes), BuyVM (monthly SLICE plans), and OVHcloud US (explicit USD starting monthly rates) are parsed separately from offers. These are **standard rates, never deals**. At least three named official rows and an actual source inspection timestamp are required before an indexed comparison page exists. The official price/usage/billing qualifications are displayed per plan. All other monitored providers without qualifying discounts or 3+ verified list prices are excluded from the sitemap and internal navigation, not populated with speculative filler. The public text for every supported scanner status is mapped via `public_copy.py`; unknown values use a human-readable fallback.

## Official pricing keyword pages

`pricing_pages.py` publishes a **single full model/specification/USD monthly-price table** for every verifiable provider (`/digitalocean-pricing/`, `/hetzner-pricing/`, `/cloudways-pricing/`, `/ovhcloud-pricing/`, `/buyvm-pricing/`). Only the independently supplied high-volume category `digitalocean droplet pricing` (590 US monthly searches, user-supplied unverified group research) has a standalone subfamily URL. The 38 previously published synthetic `/...-cost/` URLs and four DigitalOcean categories without documented search volume redirect permanently to their evidence-backed parent pricing page, rather than remaining indexable. Old `/providers/.../` list-price pages also redirect to the current pricing main page. Existing specific official deal URLs and three side-by-side vendor comparisons remain distinct. **No individual model cost search term has verified >=100 monthly searches**, so no model cost pages are published; `/buyvm-pricing/` remains the vendor's single consolidated table even though the user-supplied keyword volume for that phrase is zero. Other user-supplied US monthly estimates: `hetzner pricing` 720, `linode pricing` 720, `digitalocean pricing` 720, `vultr pricing` 480, `cloudways pricing` 260, `ovhcloud pricing` 110, `digitalocean droplet cost` 10. Those estimates have not been independently corroborated. Linode main and Vultr official price lists do not currently permit compliant automated model-by-model data collection, so their main pages are not generated. The site does not generate filler to reach a numeric sitemap target. Source loss removes unsupported pages on the next build.

## Retired list-price pages

The prior 20 plain-list-price pages are removed from the sitemap. `data/retired_deals.json` records their exact historic slugs. Each build emits a permanent 301 from those URLs to an evidence-backed provider pricing page when available, otherwise the comparison page, in `site/_redirects`, and a custom noindex `404.html` prevents unknown URLs being treated as the homepage. No historic list price is eligible for deal structured data.

## Compliance & monetization

Official source links only by default. Once a real affiliate application is approved, the **fourth pipe-delimited field** in `.ilang/site.ilang` can contain that provider's authorized HTTPS affiliate landing URL. The generated action link will then be explicitly marked as affiliate and carry `rel="nofollow sponsored"`; the independent evidence/source link and structured-data official price remain unchanged. Do not fill this field without platform approval and permission to promote on a coupon directory. No cookie injection, self-referral, trademark-bidding circumvention or invented commission claims. An eventual website sale depends on verifiable revenue, traffic, domain transferability and real buyer demand; it is not guaranteed. Informational directory only; always verify final checkout terms.

## SEO and verification

- `templates/base.html`, `index.html`, `provider.html`, `deal.html` and `compare.html` are actually used by Python, not decorative examples. They can be updated without installing dependencies.
- Detail pages have Product/Offer and BreadcrumbList JSON-LD; provider pages have Service and real Offer entries if deals exist; lists have ItemList. Schema only includes `priceValidUntil` and `availability` if the official source explicitly provides them. Rich results are not guaranteed.
- Each page has a matching canonical, Open Graph metadata and a generated 1200×630 social PNG. The sitemap is generated by `build.py` and uses `last_changed_at` for price-changing details, not a made-up build date.
- Search Console domain ownership is verified and the production sitemap has been submitted. Indexing is controlled by Google, not guaranteed by submission.
- Currently only English (`en-US`) and USD are supported. Adding `de/ja/es` requires genuinely localized sources, prices, billing and reciprocal hreflang; do not relabel US prices as local offers.
- Github and other content distribution must provide independent utility, not fabricated backlinks or automatic spam.

Site rules are described using I-Lang; see `.ilang/site.ilang`; protocol notes: https://ilang.ai.