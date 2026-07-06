# =============================================================================
# sync-deps.ps1 — Sync root-level dependencies into sports-concierge/ for ADK
# =============================================================================
# Windows PowerShell equivalent of sync-deps.sh
#
# Usage:
#   .\scripts\sync-deps.ps1
#   cd sports-concierge; agents-cli deploy
# =============================================================================

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$AdkDir = Join-Path $ProjectRoot "sports-concierge"

Write-Host "🔁 Syncing dependencies into sports-concierge/ ..."

# Copy shared modules
$modules = @("agents", "tools", "security", "database")
foreach ($module in $modules) {
    $target = Join-Path $AdkDir $module
    if (Test-Path $target) {
        Write-Host "   Already exists: $module (skipping)"
    } else {
        Write-Host "   Copying: $module/"
        Copy-Item -Recurse (Join-Path $ProjectRoot $module) $target
    }
}

# Copy requirements for reference
Copy-Item (Join-Path $ProjectRoot "requirements.txt") (Join-Path $AdkDir "requirements-root.txt") -ErrorAction SilentlyContinue

Write-Host "✅ Done. You can now deploy: cd sports-concierge; agents-cli deploy"
