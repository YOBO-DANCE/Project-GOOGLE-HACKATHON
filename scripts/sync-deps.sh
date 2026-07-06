#!/bin/bash
# =============================================================================
# sync-deps.sh — Sync root-level dependencies into sports-concierge/ for ADK
# =============================================================================
# The sports-concierge/ project is deployed to Vertex AI via agents-cli deploy.
# The build context for that deployment is sports-concierge/ only, so we need
# to copy the shared modules (agents/, tools/, security/, database/) into the
# sports-concierge/ tree before building.
#
# Usage:
#   ./scripts/sync-deps.sh
#   cd sports-concierge && agents-cli deploy
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ADK_DIR="$PROJECT_ROOT/sports-concierge"

echo "🔁 Syncing dependencies into sports-concierge/ ..."

# Copy shared modules
for module in agents tools security database; do
    if [ -d "$ADK_DIR/$module" ]; then
        echo "   Already exists: $module (skipping)"
    else
        echo "   Copying: $module/"
        cp -r "$PROJECT_ROOT/$module" "$ADK_DIR/$module"
    fi
done

# Copy requirements for reference
cp "$PROJECT_ROOT/requirements.txt" "$ADK_DIR/requirements-root.txt" 2>/dev/null || true

echo "✅ Done. You can now deploy: cd sports-concierge && agents-cli deploy"
