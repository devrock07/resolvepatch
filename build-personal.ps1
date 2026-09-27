$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    cargo +nightly build --release --locked
    if ($LASTEXITCODE -ne 0) { throw 'Rust build failed' }
    $bundle = Join-Path $PSScriptRoot 'target\personal-bundle'
    New-Item -ItemType Directory -Force -Path $bundle | Out-Null
    Copy-Item -LiteralPath 'target\release\resolvepatch.exe' -Destination $bundle -Force
    $profileBundle = Join-Path $bundle 'personal'
    New-Item -ItemType Directory -Force -Path $profileBundle | Out-Null
    Get-ChildItem -LiteralPath 'personal' -File | Copy-Item -Destination $profileBundle -Force
    Copy-Item -LiteralPath 'personal\assets' -Destination $profileBundle -Recurse -Force
    Write-Output "Personal bundle: $bundle"
} finally { Pop-Location }
