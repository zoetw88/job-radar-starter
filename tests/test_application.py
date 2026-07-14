from job_radar.application import scan_catalog
from job_radar.catalog import Catalog, Company, Source

import pytest


def test_scan_catalog_routes_each_company_to_its_official_adapter():
    catalog = Catalog(
        countries={},
        sources={
            "greenhouse": Source("official_api", "https://example/greenhouse", True),
            "lever": Source("official_api", "https://example/lever", True),
            "ashby": Source("official_api", "https://example/ashby", True),
        },
        companies={
            "GH Co": Company(("CA",), "greenhouse", "gh"),
            "Lever Co": Company(("GB",), "lever", "lever"),
            "Ashby Co": Company(("SG",), "ashby", "ashby"),
        },
    )

    def fake_get_json(url):
        if "greenhouse" in url:
            return {"jobs": [{"id": 1, "title": "Backend", "absolute_url": "https://example/1", "location": {"name": "Canada"}}]}
        if "lever" in url:
            return [{"id": "2", "text": "Platform", "hostedUrl": "https://example/2", "categories": {"location": "UK"}}]
        return {"jobs": [{"id": "3", "title": "AI", "jobUrl": "https://example/3", "location": "Singapore", "isListed": True}]}

    jobs = scan_catalog(catalog, fake_get_json)

    assert [(job.company, job.source) for job in jobs] == [
        ("GH Co", "greenhouse"),
        ("Lever Co", "lever"),
        ("Ashby Co", "ashby"),
    ]


def test_scan_catalog_reports_the_company_and_source_that_failed():
    catalog = Catalog(
        countries={},
        sources={"greenhouse": Source("official_api", "https://example", True)},
        companies={"Broken Board": Company(("CA",), "greenhouse", "broken")},
    )

    def failing_get_json(url):
        raise ValueError("response too large")

    with pytest.raises(RuntimeError, match=r"Broken Board \(greenhouse\).+response too large"):
        scan_catalog(catalog, failing_get_json)
