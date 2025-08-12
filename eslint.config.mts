import jsLint from '@eslint/js';
import tsLint from 'typescript-eslint';
import vueLint from 'eslint-plugin-vue';
import importPlugin from 'eslint-plugin-import';
import globals from "globals";
import { defineConfigWithVueTs, vueTsConfigs } from '@vue/eslint-config-typescript';

export default defineConfigWithVueTs(
  jsLint.configs.recommended,
  ...tsLint.configs.recommended,
  importPlugin.flatConfigs.recommended,
  ...vueLint.configs['flat/essential'],
  vueTsConfigs.recommended,
  {
    files: ['**/*.vue', '**/*.js', '**/*.jsx', '**/*.cjs', '**/*.mjs', '**/*.ts', '**/*.tsx', '**/*.cts', '**/*.mts'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: {
        // Ensure we have access to browser related globals like window/document
        ...globals.browser,
      }
    },
    rules: {
      'import/extensions': [
        'error',
        'ignorePackages',
        {
          '': 'never',
          ts: 'never',
          js: 'never',
          vue: 'off',
        },
      ],
      'import/prefer-default-export': 'off',
      radix: 'off',
      'dot-notation': 'off',
      'vue/no-use-v-if-with-v-for': 'warn',
      '@typescript-eslint/ban-ts-comment': 'off',
      '@typescript-eslint/no-explicit-any': 'off',
      'no-extra-boolean-cast': 'off',
      // Disable full warning, and customize the typescript one
      // Warn about unused vars unless they start with an underscore
      'no-unused-vars': 'off',
      '@typescript-eslint/no-unused-vars': [
        'warn',
        {
          argsIgnorePattern: '^_',
          varsIgnorePattern: '^_',
          caughtErrorsIgnorePattern: '^_',
        },
      ],
    },
    settings: {
      'import/resolver': {
        typescript: true,
        node: true,
      },
    },
  }
);
