param(
    [string]$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$OutputPath = (Join-Path $PSScriptRoot "..\\analysis\\source-manifest.json")
)

$resolvedRoot = (Resolve-Path $Root).Path
$outputDir = Split-Path -Parent $OutputPath

if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir | Out-Null
}

$files = Get-ChildItem -Path $resolvedRoot -Recurse -File |
    Where-Object { $_.FullName -notmatch '\\\.git\\' }

$manifest = foreach ($file in $files) {
    $hash = Get-FileHash -Path $file.FullName -Algorithm SHA256
    [PSCustomObject]@{
        relative_path = $file.FullName.Substring($resolvedRoot.Length).TrimStart('\')
        size_bytes    = $file.Length
        last_write    = $file.LastWriteTimeUtc.ToString("o")
        sha256        = $hash.Hash
    }
}

$payload = [PSCustomObject]@{
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    root             = $resolvedRoot
    files            = $manifest
}

$payload | ConvertTo-Json -Depth 4 | Set-Content -Path $OutputPath -Encoding UTF8
Write-Output "Wrote source manifest to $OutputPath"
