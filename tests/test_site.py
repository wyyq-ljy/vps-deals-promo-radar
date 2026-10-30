# ::ILANG [TYPE:python-module][ROLE:legacy-and-pricing-regression-tests]
# ::RULE{official-price-or-zero-deal, no fake offer on page}
# ::BOUNDARY{never:call paid APIs or fabricate source data}

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build as site_builder
import scraper
from config import load_config
from deal_site import valid_offers
from pricing_sources import parse_hostinger, parse_ionos

ROOT = Path(__file__).resolve().parents[1]
NS = '{http://www.sitemaps.org/schemas/sitemap/0.9}'

class TestDeals(unittest.TestCase):
    def test_config_and_replaced_sources(self):
        site, providers = load_config()
        self.assertEqual(site['locale'], 'en-US')
        self.assertGreaterEqual(len(providers), 20)
        self.assertEqual(len({p['name'] for p in providers}), len(providers))
        self.assertIn('DreamHost', [p['name'] for p in providers])
        self.assertIn('InMotion Hosting', [p['name'] for p in providers])
        self.assertIn('Ultahost', [p['name'] for p in providers])
        self.assertTrue(all(p['source_url'].startswith('https://') for p in providers))

    def test_ionos_requires_same_card_original_and_sale_and_terms(self):
        html = '''<h3>VPS S+</h3><div class="price-box large">
        <div class="savings-text"><div class="savings-banderole">Save $12</div>
        <span class="original-price">$6</span></div>
        <div class="current-price"><span class="price_value">2</span></div>
        <div class="offer-duration">for 3 months</div>
        <div>with a 1-year term</div></div></div></div>
        <strong>1 vCore</strong> CPU <strong>2 GB</strong> RAM <strong>60 GB</strong> NVMe'''
        offers = parse_ionos(html, '2026-10-30T00:00:00+00:00')
        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0]['regular_monthly_usd'], '6.00')
        self.assertEqual(offers[0]['promo_monthly_usd'], '2.00')
        self.assertEqual(offers[0]['promo_months'], 3)
        self.assertEqual(parse_ionos(html.replace('Save $12','Save $16'), 'now'), [])
        self.assertEqual(parse_ionos(html.replace('original-price','regular-price'), 'now'), [])

    def test_hostinger_requires_old_and_promo_and_upfront_match(self):
        html = '''<div class="h-pricing-card__title h-t-heading-3">KVM 1</div>
        <div class="h-pricing-card__old-price"><span class="hw-price__value">19.49</span></div>
        <div class="h-pricing-card__current-price"><span class="hw-price__value">6.49</span></div>
        <p>Today you pay $155.76 for 24 months. Renews at $11.99/mo for the same term.</p>
        1 vCPU core 4 GB RAM 50 GB NVMe disk space 4 TB bandwidth'''
        offers = parse_hostinger(html, 'now')
        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0]['discount_percent'], 67)
        self.assertEqual(offers[0]['upfront_usd'], '155.76')
        self.assertEqual(parse_hostinger(html.replace('19.49','6.49'), 'now'), [])
        self.assertEqual(parse_hostinger(html.replace('$155.76','$155.00'), 'now'), [])

    def test_old_standard_prices_never_qualify(self):
        site, providers = load_config()
        data = json.loads((ROOT/'data/offers.json').read_text(encoding='utf-8'))
        verified = valid_offers(data['offers'], providers)
        self.assertGreater(len(verified), 0)
        self.assertTrue(all(x['price_type']=='verified_discount' for x in verified))
        first = dict(verified[0])
        first['price_type'] = 'standard_list_price'
        self.assertEqual(valid_offers([first], providers), [])
        first['price_type'] = 'verified_discount'
        first['regular_monthly_usd'] = first['promo_monthly_usd']
        self.assertEqual(valid_offers([first], providers), [])

    def test_all_failed_sources_can_publish_zero_not_old_prices(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)/'offers.json'
            target.write_text('{"offers":[{"id":"old-regular-price"}]}',encoding='utf-8')
            with patch.object(scraper,'OUTPUT',target):
                with patch.object(scraper,'read_official',side_effect=PermissionError("blocked")):
                    data = scraper.collect()
            self.assertEqual(data['offers'], [])
            self.assertEqual(json.loads(target.read_text(encoding='utf-8'))['offers'], [])

    def test_sitemap_excludes_removed_20_standard_prices(self):
        site,_ = load_config()
        actual=json.loads((ROOT/'data/offers.json').read_text(encoding='utf-8'))
        offers=valid_offers(actual['offers'],load_config()[1])
        site_builder.build()
        xml=(site_builder.OUT/'sitemap.xml').read_text(encoding='utf-8')
        expected_providers = sum(1 for p in actual['providers'] if p.get('verified_deal_count',0) or len(p.get('list_prices',[]))>=3)
        self.assertEqual(xml.count('<loc>'),2+expected_providers+len(offers))
        self.assertEqual(xml.count('/deals/'),len(offers))
        self.assertNotIn('/deals/hetzner-cpx22-hel1/', xml)
        self.assertNotIn('/deals/digitalocean-basic-',xml)
        for offer in offers:
            self.assertIn('/deals/'+offer['id']+'/',xml)
            detail=(site_builder.OUT/'deals'/offer['id']/'index.html').read_text(encoding='utf-8')
            self.assertIn('What you actually save', detail)
            self.assertIn('Server configuration',detail)
            self.assertIn(offer['regular_monthly_usd'],detail)
            self.assertIn(offer['promo_monthly_usd'],detail)
            self.assertNotIn('Not specified in this pricing source',detail)

    def test_zero_offer_build_has_only_provider_and_index_urls(self):
        with patch.object(site_builder,'valid_offers',return_value=[]):
            site_builder.build()
            xml=(site_builder.OUT/'sitemap.xml').read_text(encoding='utf-8')
            home=(site_builder.OUT/'index.html').read_text(encoding='utf-8')
            active_prices = sum(1 for p in json.loads((ROOT/'data/offers.json').read_text('utf8'))['providers'] if len(p.get('list_prices',[]))>=3)
            self.assertEqual(xml.count('<loc>'),2+active_prices)
            self.assertNotIn('/deals/',xml)
            self.assertIn('No verified discounts currently.',home)
        site_builder.build()

    def test_unconfigured_domain_is_noindex(self):
        site,providers=load_config()
        with patch.object(site_builder,'load_config',return_value=({**site,'base_url':'','domain':''},providers)):
            site_builder.build()
            home=(site_builder.OUT/'index.html').read_text(encoding='utf-8')
            self.assertIn('noindex,follow',home)
            self.assertIn('Disallow: /',(site_builder.OUT/'robots.txt').read_text(encoding='utf-8'))
        site_builder.build()

    def test_retired_standard_price_urls_have_permanent_redirects(self):
        site_builder.build()
        rules=(site_builder.OUT/'_redirects').read_text(encoding='utf-8')
        entries=[line for line in rules.splitlines() if line and not line.startswith('#')]
        data=json.loads((ROOT/'data/offers.json').read_text('utf-8'))
        indexed=sum(1 for v in data['providers'] if v.get('verified_deal_count',0) or len(v.get('list_prices',[]))>=3)
        history=json.loads((ROOT/'data/retired_deals.json').read_text('utf-8'))
        offer_ids={x['id'] for x in data['offers']}
        withdrawn=sum(x not in offer_ids for x in history.get('withdrawn_deal_ids',[]))
        self.assertEqual(len(entries),20+len(load_config()[1])-indexed+withdrawn)
        self.assertIn('/deals/hetzner-cpx22-hel1/ /compare/ 301',rules)
        self.assertIn('/deals/digitalocean-basic-regular-512-mib-ram-1-vcpu-10-gib-ssd/ /providers/digitalocean/ 301',rules)
        self.assertIn('noindex',(site_builder.OUT/'404.html').read_text(encoding='utf-8'))

if __name__=='__main__':
    unittest.main()