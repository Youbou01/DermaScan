// ESLint 9 flat config. `npm run lint` fails on any warning: a warning nobody fixes is noise.
const { defineConfig } = require('eslint/config');
const expoConfig = require('eslint-config-expo/flat');
const prettierConfig = require('eslint-config-prettier/flat');

module.exports = defineConfig([
  expoConfig,
  // Must come after the other configs: turns off every rule that would fight Prettier.
  prettierConfig,
  {
    ignores: ['dist/*', '.expo/*', 'coverage/*', 'node_modules/*', 'expo-env.d.ts'],
  },
  {
    files: ['eslint.config.js'],
    languageOptions: { globals: { __dirname: 'readonly' } },
  },
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      // Needed by the type-aware rules below (no-floating-promises, ...).
      parserOptions: { projectService: true, tsconfigRootDir: __dirname },
    },
    rules: {
      // No `any`: use the types generated from the API (src/api) or `unknown` + narrowing.
      '@typescript-eslint/no-explicit-any': 'error',
      // "Type hints on every function signature": explicit return types on declared functions.
      // Inline callbacks (`items.map((i) => i.id)`) are inferred from context and stay allowed.
      '@typescript-eslint/explicit-function-return-type': [
        'error',
        {
          allowExpressions: true,
          allowTypedFunctionExpressions: true,
          allowHigherOrderFunctions: true,
        },
      ],
      '@typescript-eslint/consistent-type-imports': ['error', { fixStyle: 'inline-type-imports' }],
      // A forgotten `await` on a network call is a silent bug.
      '@typescript-eslint/no-floating-promises': 'error',
      '@typescript-eslint/no-misused-promises': 'error',
      '@typescript-eslint/ban-ts-comment': [
        'error',
        {
          'ts-expect-error': 'allow-with-description',
          'ts-ignore': true,
          'ts-nocheck': true,
        },
      ],
      'no-console': ['error', { allow: ['warn', 'error'] }],
      eqeqeq: ['error', 'always'],
    },
  },
]);
