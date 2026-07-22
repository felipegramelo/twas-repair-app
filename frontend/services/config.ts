/**
 * Centralized backend configuration.
 *
 * IMPORTANT: We force the production Railway URL here so that builds generated
 * via Emergent (which can overwrite the .env file with the Emergent preview
 * URL) still talk to the correct production backend used by both iOS and
 * Android.
 *
 * If you EVER need to test against a different backend (e.g., the Emergent
 * preview during development), set EXPO_PUBLIC_BACKEND_URL_OVERRIDE in .env
 * to the desired URL — that takes priority over the hardcoded production URL.
 */

// Hardcoded production backend (Railway). Single source of truth for builds.
const PRODUCTION_BACKEND_URL = 'https://twas-repair-app-production.up.railway.app';

// Emergent preview backend (local container) — used ONLY inside the preview URL
// so that new features/changes not yet deployed to Railway can be tested here.
// Built mobile/web bundles (EAS, Vercel) keep using PRODUCTION_BACKEND_URL.
const EMERGENT_PREVIEW_BACKEND = process.env.EXPO_PUBLIC_BACKEND_URL;

const override = process.env.EXPO_PUBLIC_BACKEND_URL_OVERRIDE;

// Runtime detection:
// - Emergent preview (*.preview.emergentagent.com) → env backend (preview container)
// - Emergent production deploy (*.emergent.host / *.emergentagent.com) → env backend
//   (the deployment system injects the correct EXPO_PUBLIC_BACKEND_URL)
// - Anything else (Vercel web, iOS/Android builds) → Railway production backend.
function _detectBackendUrl(): string {
  if (override && override.trim()) return override;
  try {
    if (typeof window !== 'undefined' && window.location && window.location.hostname) {
      const host = window.location.hostname;
      const isEmergentHost = host.endsWith('.emergentagent.com') || host.endsWith('.emergent.host');
      if (isEmergentHost && EMERGENT_PREVIEW_BACKEND) {
        return EMERGENT_PREVIEW_BACKEND;
      }
    }
  } catch {}
  return PRODUCTION_BACKEND_URL;
}

export const BACKEND_URL = _detectBackendUrl();
export const API_URL = `${BACKEND_URL}/api`;
