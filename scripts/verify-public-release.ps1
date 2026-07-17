[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) {
    $Python = (Get-Command python -ErrorAction Stop).Source
}

function Invoke-Checked {
    param(
        [Parameter(Mandatory)]
        [string]$Executable,
        [Parameter(ValueFromRemainingArguments)]
        [string[]]$Arguments
    )
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Executable failed with exit code $LASTEXITCODE"
    }
}

Push-Location $RepoRoot
try {
    # Inspect the committed working tree before any build command runs.
    $Gitleaks = Join-Path $env:USERPROFILE ".local\share\gitleaks\8.30.1\gitleaks.exe"
    if (-not (Test-Path -LiteralPath $Gitleaks)) {
        throw "gitleaks 8.30.1 is required at $Gitleaks"
    }
    $version = (& $Gitleaks version).Trim()
    if ($LASTEXITCODE -ne 0 -or $version -ne "8.30.1") {
        throw "gitleaks version mismatch: expected 8.30.1, got $version"
    }
    Invoke-Checked -Executable $Gitleaks -Arguments @(
        "dir", ".", "--no-banner", "--redact", "--exit-code", "1"
    )
    & (Join-Path $PSScriptRoot "verify-tracked-privacy.ps1") -RepoRoot $RepoRoot
    Invoke-Checked -Executable "git" -Arguments @(
        "diff", "--exit-code", "--", "dashboard/public/index.html"
    )

    # Deterministic fake-source smoke for the complete public CLI workflow.
    Invoke-Checked -Executable $Python -Arguments @(
        "-m", "pytest", "-q",
        "tests/test_public_workflow.py::test_release_gate_covers_run_export_and_delete"
    )

    # Full Python suite: python -m pytest -q
    Invoke-Checked -Executable $Python -Arguments @("-m", "pytest", "-q")

    # Generate into a temporary file, inspect it, and prove the committed
    # dashboard is exactly reproducible without overwriting the reviewed file.
    $GeneratedDashboard = Join-Path $env:TEMP (
        "job-radar-dashboard-" + [guid]::NewGuid().ToString("N") + ".html"
    )
    try {
        Invoke-Checked -Executable $Python -Arguments @(
            "-m", "job_radar", "build-dashboard",
            "--jobs", "examples/jobs.example.json",
            "--output", $GeneratedDashboard
        )
        $generated = Get-Content -LiteralPath $GeneratedDashboard -Raw
        foreach ($marker in @(
            'data-dashboard-contract="1"',
            'Example Systems',
            'Invented Labs',
            'data-testid="job-card"'
        )) {
            if (-not $generated.Contains($marker)) {
                throw "generated dashboard is missing marker: $marker"
            }
        }
        # Keep committed checks synthetic. Maintainer-specific markers belong
        # in an injected external pre-publication scan.
        $blockedDashboardMarker = "private-company-" + "sentinel.invalid"
        if ($generated.Contains($blockedDashboardMarker)) {
            throw "generated dashboard contains a blocked synthetic privacy marker"
        }
        $committedDashboard = Join-Path $RepoRoot "dashboard/public/index.html"
        if (
            (Get-FileHash -LiteralPath $GeneratedDashboard -Algorithm SHA256).Hash -ne
            (Get-FileHash -LiteralPath $committedDashboard -Algorithm SHA256).Hash
        ) {
            throw "committed dashboard does not match reproducible build output"
        }
    }
    finally {
        Remove-Item -LiteralPath $GeneratedDashboard -Force -ErrorAction SilentlyContinue
    }

    # Dashboard dependency audit and browser flow: npm audit; npm run test:browser
    Invoke-Checked -Executable "npm" -Arguments @("audit")
    Invoke-Checked -Executable "npm" -Arguments @("run", "test:browser")

    # Optional Worker: npm audit; npm test; wrangler deploy --dry-run
    Push-Location (Join-Path $RepoRoot "optional-sync\cloudflare")
    try {
        Invoke-Checked -Executable "npm" -Arguments @("audit")
        Invoke-Checked -Executable "npm" -Arguments @("run", "typecheck")
        Invoke-Checked -Executable "npm" -Arguments @("test")
        Invoke-Checked -Executable "npx" -Arguments @(
            "wrangler", "deploy", "--dry-run",
            "--outdir", (Join-Path $env:TEMP "job-radar-worker-dry-run")
        )
    }
    finally {
        Pop-Location
    }

    # Whitespace gate: git diff --check
    Invoke-Checked -Executable "git" -Arguments @("diff", "--check")
}
finally {
    Pop-Location
}
