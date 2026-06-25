/** @type {import("tailwindcss").Config} */

// Palette is driven by CSS variables (see src/index.css) so a single `.dark`
// class on <html> re-themes the whole app. Channels are stored space-separated
// (`r g b`) so Tailwind's `<alpha-value>` slash-opacity syntax keeps working.
const withVar = (name) => `rgb(var(${name}) / <alpha-value>)`;

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Neutral "ink" scale. Light = enterprise slate, dark = Discord greys.
        ink: {
          50: withVar("--ink-50"),
          100: withVar("--ink-100"),
          200: withVar("--ink-200"),
          300: withVar("--ink-300"),
          400: withVar("--ink-400"),
          500: withVar("--ink-500"),
          600: withVar("--ink-600"),
          700: withVar("--ink-700"),
          800: withVar("--ink-800"),
          900: withVar("--ink-900"),
          950: withVar("--ink-950"),
        },
        // Brand accent: Discord "blurple" family in both themes; only the very
        // light/dark tints (50/100/700) flip so active states stay legible.
        accent: {
          50: withVar("--accent-50"),
          100: withVar("--accent-100"),
          200: withVar("--accent-200"),
          300: withVar("--accent-300"),
          400: withVar("--accent-400"),
          500: withVar("--accent-500"),
          600: withVar("--accent-600"),
          700: withVar("--accent-700"),
          800: withVar("--accent-800"),
          900: withVar("--accent-900"),
        },
        // Panel/card surface that sits above the page canvas (was `bg-white`).
        surface: {
          DEFAULT: withVar("--surface"),
          raised: withVar("--surface-raised"),
        },
        success: { 500: "#16a34a", 100: "#dcfce7" },
        warning: { 500: "#d97706", 100: "#fef3c7" },
        danger:  { 500: "#dc2626", 100: "#fee2e2" },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      boxShadow: {
        card: "0 1px 2px 0 rgb(0 0 0 / 0.04), 0 1px 3px 0 rgb(0 0 0 / 0.06)",
        elev: "0 4px 12px -2px rgb(0 0 0 / 0.10), 0 2px 4px -2px rgb(0 0 0 / 0.06)",
      },
    },
  },
  plugins: [],
};
