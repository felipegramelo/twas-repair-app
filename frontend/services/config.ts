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

const override = process.env.EXPO_PUBLIC_BACKEND_URL_OVERRIDE;

export const BACKEND_URL = (override && override.trim()) || PRODUCTION_BACKEND_URL;
export const API_URL = `${BACKEND_URL}/api`;
