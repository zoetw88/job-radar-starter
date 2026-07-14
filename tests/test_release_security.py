from pathlib import Path


def test_gitleaks_runs_for_pushes_and_pull_requests():
    workflow = Path(".github/workflows/gitleaks.yml")

    assert workflow.exists()
    text = workflow.read_text(encoding="utf-8")
    assert "push:" in text
    assert "pull_request:" in text
    assert "gitleaks/gitleaks-action" in text
    assert "actions/checkout@v6" in text
    assert "gitleaks/gitleaks-action@v3" in text
