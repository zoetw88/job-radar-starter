from pathlib import Path

from job_radar.catalog import load_catalog


def test_public_catalog_separates_sources_from_user_preferences(tmp_path: Path):
    catalog_file = tmp_path / "sources.yaml"
    catalog_file.write_text(
        """
countries:
  CA:
    name: Canada
    sources: [greenhouse, lever]
  SG:
    name: Singapore
    sources: [ashby]
sources:
  greenhouse:
    kind: official_api
    terms_url: https://developer.greenhouse.io/job-board.html
    enabled: true
companies:
  Shopify:
    countries: [CA]
    source: greenhouse
    board: shopify
""".strip(),
        encoding="utf-8",
    )

    catalog = load_catalog(catalog_file)

    assert catalog.countries["CA"].sources == ("greenhouse", "lever")
    assert catalog.countries["SG"].name == "Singapore"
    assert catalog.sources["greenhouse"].kind == "official_api"
    assert catalog.sources["greenhouse"].enabled is True
    assert catalog.companies["Shopify"].board == "shopify"
    assert catalog.companies["Shopify"].countries == ("CA",)
