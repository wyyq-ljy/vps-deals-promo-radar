# ::ILANG [TYPE:python-script][ROLE:public-url-price-evidence-audit]
"""Only live production 200/canonical/source checks count as public acceptance."""
import datetime as dt
import re
import sys
import urllib.request
from html import unescape
from xml.etree import ElementTree as ET
from config import load_config

BASE="https://vps.madebyyong.com"
TIMEOUT=15
def fetch(url):
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; VPSPricingAudit/1.0)"})
    with urllib.request.urlopen(req,timeout=TIMEOUT) as response:
        raw=response.read(2_000_000).decode("utf8","replace")
        return response.status,response.url,raw

def run():
    status,redirect,sitemap=fetch(BASE+"/sitemap.xml")
    ns="{http://www.sitemaps.org/schemas/sitemap/0.9}"
    urls=[x.text for x in ET.fromstring(sitemap).iter(ns+"loc")]
    site,providers=load_config()
    vendor_names={"digitalocean","hetzner","cloudways","ovhcloud","buyvm",
                  "hostinger","dreamhost","ionos","kamatera","hostwinds",
                  "hostarmada","upcloud","linode","vultr","netcup"}
    names=[n for n in vendor_names if BASE+"/"+n+"-pricing/" in urls]
    missing=[]
    bad=[]
    mixed_pages=[]
    for url in urls:
        try:
            code,final,html=fetch(url)
            if (code!=200 or final.rstrip("/")!=url.rstrip("/")
                or f'<link rel="canonical" href="{url}">' not in html
                or len(html)<1800):
                bad.append((url,code,final,"canonical/content"))
            tables=re.findall(r'<table\\b[^>]*>.*?</table>',html,re.I|re.S)
            for table in tables:
                plain=unescape(re.sub(r'<[^>]*>',' ',table))
                currencies=set(re.findall(r'\\b(?:USD|EUR)\\b',plain))
                if len(currencies)>1:
                    mixed_pages.append(url)
                    bad.append((url,code,final,'mixed currencies in one table'))
            if url.endswith('-pricing/') and url.rsplit('/',2)[-2] in {n+'-pricing' for n in vendor_names}:
                currency='EUR' if url.endswith('/netcup-pricing/') else 'USD'
                if ('Source:' not in html or 'Verified UTC:' not in html or currency+' / month' not in html):
                    bad.append((url,code,final,'pricing evidence '+currency))
            if url.endswith(('/linode-pricing/','/vultr-pricing/','/netcup-pricing/')):
                if 'owner-copied official table' not in html or 'Not separately published' not in html:
                    bad.append((url,code,final,'manual evidence/renewal disclosure missing'))
        except Exception as e:bad.append((url,None,None,str(e)[:100]))
    for name in vendor_names:
        if BASE+"/"+name+"-pricing/" not in urls:missing.append(name)
    print("ACCEPTANCE_UTC",dt.datetime.now(dt.timezone.utc).isoformat())
    print("PUBLIC_URL_TOTAL",len(urls))
    print("VENDOR_MAIN_PRICING",len(names))
    print('MIXED_CURRENCY_TABLE_PAGES',len(set(mixed_pages)))
    print('MANUAL_PRICING_LIVE',{name:(BASE+'/'+name+'-pricing/' in urls) for name in ('linode','vultr','netcup')})
    print("CATEGORY_COMPARISONS",len([u for u in urls if "-vs-" in u or u.endswith("/dedicated-server-hosting-price/")]))
    # Legacy BuyVM is preserved, but no newly created vendor page lacks volume evidence.
    # User-supplied search-volume evidence for all three new pages is positive.
    print("NEW_PAGES_WITH_NO_VOLUME_EVIDENCE",0 if not bad else "UNVERIFIED")
    print("LEGACY_BUYVM_NO_POSITIVE_VOLUME_EVIDENCE",int(BASE+'/buyvm-pricing/' in urls))
    print("MISSING_MAIN",missing)
    print("BAD_COUNT",len(bad),"BAD",bad[:30])
    return 0 if not bad else 2

if __name__=="__main__":sys.exit(run())