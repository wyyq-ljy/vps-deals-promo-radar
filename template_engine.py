# ::ILANG [TYPE:python-module][ROLE:deterministic-html-template-renderer]
# ::RULE{templates are local versioned files; data must be escaped by callers}
# ::BOUNDARY{never:fetch remote markup or execute templates}
"""Small dependency-free HTML template loader."""
from string import Template
from config import ROOT

def render(filename, **variables):
    if filename not in {"base.html", "index.html", "provider.html", "provider_standard.html", "deal.html", "compare.html"}:
        raise ValueError("Unexpected template name")
    text = (ROOT / "templates" / filename).read_text(encoding="utf-8")
    return Template(text).substitute(variables)