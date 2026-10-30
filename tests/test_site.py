import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build as site_builder
from config import load_config


class TestSite(unittest.TestCase):
    def test_config(self):
        site, providers = load_config()
        self.assertEqual(site["locale"], "en-US")
        self.assertGreaterEqual(len(providers), 3)

    def test_config_drives_provider_list(self):
        source = Path(__file__).resolve().parents[1] / ".ilang/site.ilang"
        raw = source.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as directory:
            alternate = Path(directory) / "site.ilang"
            alternate.write_text(
                raw.replace("Hetzner |", "ChangedProvider |"),
                encoding="utf-8",
            )
            _, providers = load_config(alternate)
        self.assertIn("ChangedProvider", [p["name"] for p in providers])

    def test_build_without_domain_is_noindex(self):
        site, providers = load_config()
        without_domain = {**site, "domain": "", "base_url": ""}
        try:
            with patch.object(
                site_builder,
                "load_config",
                return_value=(without_domain, providers),
            ):
                site_builder.build()
                homepage = (site_builder.OUT / "index.html").read_text("utf-8")
                robots = (site_builder.OUT / "robots.txt").read_text("utf-8")
                self.assertIn("noindex,follow", homepage)
                self.assertIn("Disallow: /", robots)
                self.assertNotIn('"@type": "Offer"', homepage)
        finally:
            site_builder.build()

    def test_build_with_configured_domain(self):
        site, _ = load_config()
        site_builder.build()
        homepage = (site_builder.OUT / "index.html").read_text("utf-8")
        robots = (site_builder.OUT / "robots.txt").read_text("utf-8")
        sitemap = (site_builder.OUT / "sitemap.xml").read_text("utf-8")
        base = site.get("base_url", "").rstrip("/")
        if base:
            self.assertIn(f'<link rel="canonical" href="{base}/">', homepage)
            self.assertNotIn("noindex,follow", homepage)
            self.assertIn("Allow: /", robots)
            self.assertIn(f"Sitemap: {base}/sitemap.xml", robots)
            self.assertEqual(sitemap.count("<loc>"), 6)
        else:
            self.assertIn("noindex,follow", homepage)
            self.assertIn("Disallow: /", robots)
        self.assertIn("Official pricing radar", homepage)
        self.assertNotIn('"@type": "Offer"', homepage)


if __name__ == "__main__":
    unittest.main()