import tseslint from "typescript-eslint";

// Lint without `eslint-config-next`'s babel-parser dependency (which CJS
// hoisting can't resolve for this monorepo). TS-ESLint is the official
// Next.js recommendation for typescript linting; we add a small set
// of stricter checks via overrides.

export default tseslint.config(
  {
    ignores: [
      ".next/**",
      "node_modules/**",
      "dist/**",
      "next-env.d.ts",
      "*.config.js",
      "*.config.mjs",
    ],
  },
  ...tseslint.configs.recommended,
  {
    files: ["**/*.ts", "**/*.tsx"],
    rules: {
      "@typescript-eslint/no-unused-vars": [
        "warn",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
      "@typescript-eslint/no-explicit-any": "warn",
      "@typescript-eslint/consistent-type-imports": [
        "warn",
        { prefer: "type-imports", fixStyle: "inline-type-imports" },
      ],
      "@typescript-eslint/no-require-imports": "off",
      "no-console": ["warn", { allow: ["warn", "error"] }],
    },
  }
);
