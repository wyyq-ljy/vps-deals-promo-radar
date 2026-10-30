# ::ILANG [TYPE:python-module][ROLE:site-config]
# ::RULE{read:.ilang/site.ilang as sole provider/config source}
# ::BOUNDARY{never:hardcode provider records}
"""Strict minimal parser for the I-Lang site configuration subset used here."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent


def load_config(path=None):
    content = Path(path or ROOT / '.ilang/site.ilang').read_text(encoding='utf-8')
    state = re.search(r'::STATE\{@SITE,\s*(.*?)\}', content)
    if not state:
        raise ValueError('Missing @SITE configuration')
    metadata = dict(re.findall(r'([a-z_]+):([^,}]*)', state.group(1)))
    metadata = {k: v.strip() for k,v in metadata.items()}
    part = content.split('::MODULE{PROVIDERS', 1)
    if len(part) < 2:
        raise ValueError('Missing PROVIDERS module')
    body = part[1].split('\n', 1)[-1].split('::MODULE{', 1)[0]
    providers = []
    for raw in body.splitlines():
        if '|' not in raw: continue
        cells = [c.strip() for c in raw.split('|')]
        if len(cells) != 4: raise ValueError('Provider requires exactly four pipe-delimited fields')
        name, website, source, affiliate = cells
        if not (name and website.startswith('https://') and source.startswith('https://')):
            raise ValueError('Invalid provider configuration')
        providers.append({'name':name,'website':website,'source_url':source,'affiliate_url':affiliate})
    if not providers: raise ValueError('No providers configured')
    return metadata, providers