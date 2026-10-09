import { useCallback, useEffect, useState } from "react";

/** The user's choice. "system" follows the OS `prefers-color-scheme` and tracks changes to it. */
export type Theme = "light" | "dark" | "system";

/** Must match the inline script in index.html, which applies the theme before React renders. */
export const THEME_STORAGE_KEY = "aegis.theme";
export const THEME_ORDER: Theme[] = ["light", "dark", "system"];

const DARK_QUERY = "(prefers-color-scheme: dark)";

export function readStoredTheme(): Theme {
  try {
    const value = localStorage.getItem(THEME_STORAGE_KEY);
    return value === "light" || value === "dark" ? value : "system";
  } catch {
    return "system"; // storage blocked (private mode, sandboxed iframe)
  }
}

export function applyTheme(theme: Theme): void {
  const dark = theme === "dark" || (theme === "system" && window.matchMedia(DARK_QUERY).matches);
  document.documentElement.classList.toggle("dark", dark);
}

export function useTheme(): [Theme, (theme: Theme) => void] {
  const [theme, setThemeState] = useState<Theme>(readStoredTheme);

  const setTheme = useCallback((next: Theme) => {
    try {
      if (next === "system") localStorage.removeItem(THEME_STORAGE_KEY);
      else localStorage.setItem(THEME_STORAGE_KEY, next);
    } catch {
      // the choice then lasts only for this page load
    }
    setThemeState(next);
  }, []);

  useEffect(() => {
    applyTheme(theme);
    if (theme !== "system") return;
    const media = window.matchMedia(DARK_QUERY);
    const onChange = () => applyTheme("system");
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, [theme]);

  return [theme, setTheme];
}
