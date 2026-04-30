param(
    [Parameter(Mandatory = $true)]
    [string]$SamplePath,
    [string]$OutputPath
)

if (-not (Test-Path $SamplePath)) {
    throw "Sample not found: $SamplePath"
}

if (-not $OutputPath) {
    $OutputPath = Join-Path $PSScriptRoot "..\\analysis\\sample-inspection.json"
}

$resolvedSample = (Resolve-Path $SamplePath).Path
$outputDir = Split-Path -Parent $OutputPath

if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir | Out-Null
}

$file = Get-Item $resolvedSample
$sha256 = Get-FileHash -Path $resolvedSample -Algorithm SHA256
$signature = Get-AuthenticodeSignature -FilePath $resolvedSample

$stream = [System.IO.File]::Open($resolvedSample, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
try {
    $buffer = New-Object byte[] 64
    $bytesRead = $stream.Read($buffer, 0, $buffer.Length)
} finally {
    $stream.Dispose()
}

$headerBytes = $buffer[0..($bytesRead - 1)] | ForEach-Object { $_.ToString("X2") }
$mzHeader = $bytesRead -ge 2 -and $buffer[0] -eq 0x4D -and $buffer[1] -eq 0x5A

$result = [PSCustomObject]@{
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    sample_path      = $resolvedSample
    size_bytes       = $file.Length
    created_utc      = $file.CreationTimeUtc.ToString("o")
    modified_utc     = $file.LastWriteTimeUtc.ToString("o")
    attributes       = $file.Attributes.ToString()
    sha256           = $sha256.Hash
    authenticode     = [PSCustomObject]@{
        status         = $signature.Status.ToString()
        status_message = $signature.StatusMessage
        signer_subject = if ($signature.SignerCertificate) { $signature.SignerCertificate.Subject } else { $null }
    }
    pe_header        = [PSCustomObject]@{
        has_mz_header = $mzHeader
        first_64_hex  = ($headerBytes -join " ")
    }
}

$result | ConvertTo-Json -Depth 5 | Set-Content -Path $OutputPath -Encoding UTF8
Write-Output "Wrote sample inspection to $OutputPath"
