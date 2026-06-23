import type { TokenPairResponse } from "@/types/api";

const ACCESS_KEY = "imigrai_access_token";
const REFRESH_KEY = "imigrai_refresh_token";
const ACCESS_COOKIE = "imigrai_access_token";

function isBrowser(): boolean {
  return typeof globalThis.window !== "undefined";
}

export function getAccessToken(): string | null {
  if (!isBrowser()) {
    return null;
  }
  return globalThis.window.localStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken(): string | null {
  if (!isBrowser()) {
    return null;
  }
  return globalThis.window.localStorage.getItem(REFRESH_KEY);
}

function setAccessCookie(token: string): void {
  if (!isBrowser()) {
    return;
  }

  document.cookie = `${ACCESS_COOKIE}=${encodeURIComponent(token)}; Path=/; Max-Age=1800; SameSite=Lax`;
}

function clearAccessCookie(): void {
  if (!isBrowser()) {
    return;
  }

  document.cookie = `${ACCESS_COOKIE}=; Path=/; Max-Age=0; SameSite=Lax`;
}

export function setAuthTokens(tokens: TokenPairResponse): void {
  if (!isBrowser()) {
    return;
  }

  globalThis.window.localStorage.setItem(ACCESS_KEY, tokens.access_token);
  globalThis.window.localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
  setAccessCookie(tokens.access_token);
}

export function clearAuthTokens(): void {
  if (!isBrowser()) {
    return;
  }

  globalThis.window.localStorage.removeItem(ACCESS_KEY);
  globalThis.window.localStorage.removeItem(REFRESH_KEY);
  clearAccessCookie();
}
