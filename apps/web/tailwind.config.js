/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: "class",
  content: ["./src/**/*.{ts,tsx,js,jsx,mdx}"],
  theme: {
    container: {
      center: true,
      padding: { DEFAULT: "1rem", lg: "1.5rem" },
      screens: { "2xl": "1280px" },
    },
    extend: {
      fontFamily: {
        sans: [
          "var(--font-sans)",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
        serif: ["var(--font-serif)", "ui-serif", "Georgia", "Cambria", "serif"],
        mono: [
          "var(--font-mono)",
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Consolas",
          "monospace",
        ],
      },
      fontSize: {
        "2xs": ["0.6875rem", { lineHeight: "1rem" }],
      },
      colors: {
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",

        surface: {
          DEFAULT: "hsl(var(--surface))",
          foreground: "hsl(var(--surface-foreground))",
          hover: "hsl(var(--surface-hover))",
          sunken: "hsl(var(--surface-sunken))",
        },
        sidebar: {
          DEFAULT: "hsl(var(--sidebar))",
          foreground: "hsl(var(--sidebar-foreground))",
          hover: "hsl(var(--sidebar-hover))",
        },

        muted: "hsl(var(--muted))",
        "muted-foreground": "hsl(var(--muted-foreground))",
        card: "hsl(var(--card))",
        "card-foreground": "hsl(var(--card-foreground))",
        popover: "hsl(var(--popover))",
        "popover-foreground": "hsl(var(--popover-foreground))",
        border: "hsl(var(--border))",
        "border-strong": "hsl(var(--border-strong))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",

        primary: "hsl(var(--primary))",
        "primary-foreground": "hsl(var(--primary-foreground))",
        "primary-soft": "hsl(var(--primary-soft))",
        "primary-soft-foreground": "hsl(var(--primary-soft-foreground))",

        accent: "hsl(var(--accent))",
        "accent-foreground": "hsl(var(--accent-foreground))",

        success: "hsl(var(--success))",
        "success-foreground": "hsl(var(--success-foreground))",
        "success-soft": "hsl(var(--success-soft))",
        "success-soft-foreground": "hsl(var(--success-soft-foreground))",

        warning: "hsl(var(--warning))",
        "warning-foreground": "hsl(var(--warning-foreground))",
        "warning-soft": "hsl(var(--warning-soft))",
        "warning-soft-foreground": "hsl(var(--warning-soft-foreground))",

        info: "hsl(var(--info))",
        "info-foreground": "hsl(var(--info-foreground))",
        "info-soft": "hsl(var(--info-soft))",
        "info-soft-foreground": "hsl(var(--info-soft-foreground))",

        danger: "hsl(var(--danger))",
        "danger-foreground": "hsl(var(--danger-foreground))",
        "danger-soft": "hsl(var(--danger-soft))",
        "danger-soft-foreground": "hsl(var(--danger-soft-foreground))",

        destructive: "hsl(var(--destructive))",
        "destructive-foreground": "hsl(var(--destructive-foreground))",
      },
      borderRadius: {
        xl: "calc(var(--radius) + 6px)",
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      boxShadow: {
        soft: "var(--shadow-soft)",
        card: "var(--shadow-card)",
        raised: "var(--shadow-raised)",
        overlay: "var(--shadow-overlay)",
      },
      transitionTimingFunction: {
        "out-expo": "cubic-bezier(0.22, 1, 0.36, 1)",
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
        "fade-in": {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        "slide-up": {
          from: { opacity: "0", transform: "translateY(6px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "scale-in": {
          from: { opacity: "0", transform: "scale(0.97)" },
          to: { opacity: "1", transform: "scale(1)" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        "fade-in": "fade-in 0.2s ease-out",
        "slide-up": "slide-up 0.24s cubic-bezier(0.22, 1, 0.36, 1)",
        "scale-in": "scale-in 0.16s cubic-bezier(0.22, 1, 0.36, 1)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
