import { THEME_ORDER, useTheme, type Theme } from "../theme";

const LABELS: Record<Theme, string> = { light: "Light", dark: "Dark", system: "System" };

function ThemeIcon({ theme }: { theme: Theme }) {
  const common = {
    viewBox: "0 0 24 24",
    className: "h-5 w-5",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 2,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
  };
  if (theme === "light") {
    return (
      <svg {...common}>
        <circle cx="12" cy="12" r="4" />
        <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
      </svg>
    );
  }
  if (theme === "dark") {
    return (
      <svg {...common}>
        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79Z" />
      </svg>
    );
  }
  return (
    <svg {...common}>
      <rect x="2" y="4" width="20" height="13" rx="2" />
      <path d="M8 21h8M12 17v4" />
    </svg>
  );
}

/** Cycles Light → Dark → System. The icon shows the current choice; the label also names the next one. */
export function ThemeToggle() {
  const [theme, setTheme] = useTheme();
  const next = THEME_ORDER[(THEME_ORDER.indexOf(theme) + 1) % THEME_ORDER.length];
  const label = `Theme: ${LABELS[theme]}. Switch to ${LABELS[next]}.`;
  return (
    <button
      type="button"
      data-testid="theme-toggle"
      aria-label={label}
      title={label}
      onClick={() => setTheme(next)}
      className="rounded-md p-2 text-slate-700 hover:bg-slate-200 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 dark:text-slate-300 dark:hover:bg-slate-800 dark:focus-visible:outline-indigo-400"
    >
      <ThemeIcon theme={theme} />
    </button>
  );
}
