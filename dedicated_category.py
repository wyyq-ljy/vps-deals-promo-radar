# ::ILANG [TYPE:python-module][ROLE:dedicated-server-category-snapshot]
"""Dedicated physical-server pricing, official one-page, live revalidated."""
import re
from config import ROOT
from pricing_sources import plain
from standard_prices import row

SOURCE="https://www.inmotionhosting.com/dedicated-servers"

def snapshots():
    content=(ROOT/".ilang/site.ilang").read_text(encoding="utf8")
    part=content.split("::MODULE{DEDICATED_SNAPSHOTS",1)
    if len(part)!=2:return []
    body=part[1].split("\n",1)[-1].split("::MODULE{",1)[0]
    result=[]
    for line in body.splitlines():
        if not line.startswith("DEDICATED | "):continue
        fields=[f.strip() for f in line.split(" | ")]
        if len(fields)!=10:raise ValueError("Dedicated snapshot needs 9 fields after prefix")
        _,model,monthly,cpu,memory,storage,transfer,source,checked,note=fields
        if source!=SOURCE or not all(fields):raise ValueError("Invalid dedicated source evidence")
        result.append(dict(model=model,monthly_usd=monthly,currency="USD",
            cpu=cpu,memory=memory,storage=storage,transfer=transfer,
            source_url=source,checked_at=checked,price_note=note))
    return result

def live_verify(html,checked):
    """Each planned row must match a current first-party offer and its specs."""
    text=plain(html)
    result=[]
    for saved in snapshots():
        marker=saved["model"]+" $"+saved["monthly_usd"]+" /mo For 12 month term"
        index=text.find(marker)
        if index<0:continue
        segment=text[index:index+650].split(" Dedicated IPs",1)[0]
        # Require price, monthly billing term and physical plan's CPU/RAM/SSD.
        if not all(token in segment for token in (
            saved["cpu"],saved["memory"],saved["storage"],"Unmetered Bandwidth")):
            continue
        item=dict(saved,checked_at=checked)
        result.append(item)
    return result if len(result)>=3 and len({x["model"] for x in result})==len(result) else []
