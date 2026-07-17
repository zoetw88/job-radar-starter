[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$RepoRoot,
    [string[]]$TrackedPaths,
    [string[]]$BlockedMarkers,
    [string[]]$AllowedPathLines
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Read-TrackedText {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    $bytes = [System.IO.File]::ReadAllBytes($Path)
    if ($bytes.Length -ge 2 -and $bytes[0] -eq 0xff -and $bytes[1] -eq 0xfe) {
        $encoding = [System.Text.UnicodeEncoding]::new($false, $true, $true)
        $text = $encoding.GetString($bytes, 2, $bytes.Length - 2)
    }
    elseif ($bytes.Length -ge 2 -and $bytes[0] -eq 0xfe -and $bytes[1] -eq 0xff) {
        $encoding = [System.Text.UnicodeEncoding]::new($true, $true, $true)
        $text = $encoding.GetString($bytes, 2, $bytes.Length - 2)
    }
    else {
        $offset = if (
            $bytes.Length -ge 3 -and
            $bytes[0] -eq 0xef -and
            $bytes[1] -eq 0xbb -and
            $bytes[2] -eq 0xbf
        ) { 3 } else { 0 }
        $encoding = [System.Text.UTF8Encoding]::new($false, $true)
        $text = $encoding.GetString($bytes, $offset, $bytes.Length - $offset)
    }
    if ($text.Contains([char]0)) {
        throw "tracked text contains an embedded NUL: $Path"
    }
    return $text
}

$root = (Resolve-Path -LiteralPath $RepoRoot).Path
if (-not $TrackedPaths) {
    Push-Location $root
    try {
        $TrackedPaths = @(git ls-files)
        if ($LASTEXITCODE -ne 0) {
            throw "privacy scan could not enumerate tracked files"
        }
    }
    finally {
        Pop-Location
    }
}
if (-not $TrackedPaths) {
    throw "privacy scan could not enumerate tracked files"
}

$syntheticSentinel = "private-owner-" + "sentinel.invalid"
if (-not $BlockedMarkers) {
    $injected = $env:JOB_RADAR_PRIVATE_MARKERS
    $BlockedMarkers = if ($injected) {
        @($injected.Split(";", [System.StringSplitOptions]::RemoveEmptyEntries))
    }
    else {
        @($syntheticSentinel)
    }
}
if (-not $BlockedMarkers -or $BlockedMarkers.Where({ -not $_.Trim() }).Count -gt 0) {
    throw "privacy scan requires non-empty blocked markers"
}
$injectedAllowed = $env:JOB_RADAR_PRIVACY_ALLOWED_PATH_LINES
if (-not $AllowedPathLines -and $injectedAllowed) {
    $AllowedPathLines = @(
        $injectedAllowed.Split(";", [System.StringSplitOptions]::RemoveEmptyEntries)
    )
}
$allowed = [System.Collections.Generic.HashSet[string]]::new(
    [System.StringComparer]::Ordinal
)
if ($AllowedPathLines) {
    foreach ($entry in $AllowedPathLines) {
        if (-not $entry -or -not $entry.Contains("::")) {
            throw "privacy allowed lines must use relative/path::exact line"
        }
        [void]$allowed.Add($entry)
    }
}
$effectiveMarkers = @($BlockedMarkers) + @($syntheticSentinel)
$privacyPattern = ($effectiveMarkers | ForEach-Object {
    [regex]::Escape($_)
}) -join "|"
if (-not [regex]::IsMatch($syntheticSentinel, $privacyPattern, "IgnoreCase")) {
    throw "privacy scan self-test failed"
}

$blocked = [System.Collections.Generic.List[string]]::new()
foreach ($trackedPath in $TrackedPaths) {
    $absolute = if ([System.IO.Path]::IsPathRooted($trackedPath)) {
        [System.IO.Path]::GetFullPath($trackedPath)
    }
    else {
        [System.IO.Path]::GetFullPath((Join-Path $root $trackedPath))
    }
    if (-not (Test-Path -LiteralPath $absolute -PathType Leaf)) {
        throw "tracked privacy path is not a file: $trackedPath"
    }
    $rootPrefix = $root.TrimEnd("\", "/") + [System.IO.Path]::DirectorySeparatorChar
    $relative = if ($absolute.StartsWith($rootPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        $absolute.Substring($rootPrefix.Length).Replace("\", "/")
    }
    else {
        $absolute.Replace("\", "/")
    }
    $lines = (Read-TrackedText -Path $absolute) -split "\r?\n"
    for ($index = 0; $index -lt $lines.Length; $index++) {
        $line = $lines[$index]
        if (-not [regex]::IsMatch($line, $privacyPattern, "IgnoreCase")) {
            continue
        }
        $trimmed = $line.Trim()
        if ($allowed.Contains($relative + "::" + $trimmed)) {
            continue
        }
        $blocked.Add("${relative}:$($index + 1):$trimmed")
    }
}

if ($blocked.Count -gt 0) {
    $blocked | ForEach-Object { [Console]::Error.WriteLine($_) }
    throw "privacy scan found blocked metadata"
}
Write-Output "privacy scan passed for $($TrackedPaths.Count) tracked files"
