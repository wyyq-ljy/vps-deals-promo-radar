# ::ILANG [TYPE:python-module][ROLE:manual-firstparty-official-pricing]
# ::BOUNDARY{never:robots bypass; third-party data; EUR-to-USD conversion; stale quotes}
"""Human-transcribed, first-party rows. No automated request to blocked websites."""
import datetime as dt
from decimal import Decimal, InvalidOperation
from pathlib import Path
from config import ROOT, load_config

MANUAL_NAMES = ("Linode", "Vultr", "Netcup")
MAX_MANUAL_AGE_DAYS = 30
REQUIRED = ("model", "monthly_usd", "currency", "cpu", "memory", "storage",
            "transfer", "source_url", "checked_at", "price_note")


def read_manual(path=None, now=None):
    """Read static owner-supplied quotations; expire them unless refreshed by a human."""
    content = Path(path or ROOT / ".ilang/site.ilang").read_text("utf8")
    parts = content.split("::MODULE{MANUAL_VERIFIED_PRICING", 1)
    if len(parts) != 2:
        return {}
    body = parts[1].split("\n", 1)[-1].split("::MODULE{", 1)[0]
    _, configured = load_config()
    sources = {p["name"]: p["source_url"] for p in configured}
    now = now or dt.datetime.now(dt.timezone.utc)
    result = {}
    for line in body.splitlines():
        if not line.startswith("MANUAL | "):
            continue
        fields = [v.strip() for v in line.split(" | ")]
        if len(fields) != 15:
            raise ValueError("Manual first-party quote must contain all 14 fields")
        (_, provider, model, amount, currency, cpu, ram, disk, transfer,
         source, checked, kind, reference, renewal, note) = fields
        if provider not in MANUAL_NAMES or source != sources.get(provider):
            raise ValueError("Unknown manual provider or mismatched official source")
        if currency != ("EUR" if provider == "Netcup" else "USD"):
            raise ValueError("Unexpected currency for manual vendor")
        if kind not in ("standard", "term_discount") or (kind == "term_discount") != (provider == "Netcup"):
            raise ValueError("Quote type inconsistent with official table")
        if not all((model, cpu, ram, disk, transfer, note)) or not source.startswith("https://"):
            raise ValueError("Incomplete manual provider quote")
        try:
            month = Decimal(amount)
            ref = Decimal(reference) if reference != "-" else None
            renewed = Decimal(renewal) if renewal != "-" else None
            when = dt.datetime.fromisoformat(checked.replace("Z", "+00:00"))
        except (ValueError, InvalidOperation) as exc:
            raise ValueError("Unparseable first-party manual quote") from exc
        if (month <= 0 or month > 100000 or
                (ref is not None and ref <= month) or
                (renewed is not None and renewed <= 0) or when.tzinfo is None):
            raise ValueError("Invalid manual amount, reference or verification time")
        if (when - now).total_seconds() > 300:
            raise ValueError("Manual verification timestamp is in the future")
        if now - when > dt.timedelta(days=MAX_MANUAL_AGE_DAYS):
            continue
        if provider == "Netcup" and ref is None:
            raise ValueError("Netcup requires official EUR comparison price")
        if provider != "Netcup" and ref is not None:
            raise ValueError("Ordinary rates must not be called promotional")
        result.setdefault(provider, []).append(dict(
            model=model, monthly_usd=amount, currency=currency,
            cpu=cpu, memory=ram, storage=disk, transfer=transfer,
            source_url=source, checked_at=checked, price_note=note,
            rate_kind=kind, reference_monthly=reference,
            renewal_monthly=renewal, evidence_kind="owner_manual_firstparty"))
    for provider, rows in result.items():
        if len(rows) < 3 or len({r["model"] for r in rows}) != len(rows):
            raise ValueError("Manual provider must have at least three distinct official plans")
        if len({r["currency"] for r in rows}) != 1:
            raise ValueError("Mixed currency within one pricing page")
    return result


def with_manual_prices(data, configured=None, now=None):
    """Overlay only fresh first-party human evidence during build or scraper run."""
    active = read_manual(now=now)
    providers = data.setdefault("providers", [])
    found = {p["name"]: p for p in providers}
    sources = {p["name"]: p["source_url"] for p in (configured or load_config()[1])}
    for name in MANUAL_NAMES:
        record = found.get(name)
        if record is None:
            record = {"name": name, "source_url": sources[name], "status": "manual_quote_expired"}
            providers.append(record)
        record["list_prices"] = active.get(name, [])
        record["status"] = ("owner_manual_firstparty_verified" if name in active
                            else "manual_quote_expired")
        record["source_url"] = sources[name]
    return data