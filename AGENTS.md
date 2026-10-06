# Thunderbird Accounts — agent guide

"Accounts" provides "settings" for the Thundermail webmail service.

This document is a guide for agents and contributors.

The frontend is in Vue 3 and stored in ./assets/ and the backend is Django, in ./src.
See AGENTS.md files in those dirs for specific guidance on those parts.

# Commit messages

The first line of a commit message is one single, short sentence that starts with a capitalized verb (120 characters max). For more complex commits, add two short sentences or paragraphs separated by a blank line in the form of "Before...\n\nNow..."
 1-2 explanatory sentences as a body below, separated by a blank line. Do not include opinions and detailed research, stick to the precise facts of what was implemented in the commit.

Use a commit style similar to the other commits in the repository, don't randomly introduce conventional commit or any other types of tags.

When a commit closes a GitHub issue, append the issue reference in the historical format: `Commit message sentence. (Fixes #123)`.

When a commit only relates to an issue without fixing it — follow-up work on an issue another commit already closed, partial progress, or a change whose context lives in that issue — reference it without the verb instead: `Commit message sentence. (#123)`. Reserve `Fixes` for the commit that actually closes the issue, so a reference never claims a fix it did not deliver.

# Code comments

Comments describe what the current code does and the constraints it must
satisfy. Do not narrate how the code used to behave or explain a fixed
bug at length. Concise references or links to fixed issues are acceptable;
detailed history belongs in the commit message and the issue.

Keep comments tight and strictly factual. Do not restate what the code
plainly does. Where a non-obvious constraint comes from a spec, cite the
requirement id (for example `FM-6.9`) or the RFC section instead of
explaining its background. The same applies to test comments: state what
the test pins, not which regression prompted it.

This governs comments you write. Leave existing comments alone, even
where they break the rule — do not rewrite them unless asked.

## Planning features and bug fixes

When implementing something new or fixing a bug, always search and review related literature.
For example if the implementation would touch JMAP code, review the JMAP spec and Stalwart's
code, as Stalwart is our reference implementation of JMAP.

Ensure to look for libraries that can supply functionality you need for the implementation. This is especially important when performing calculations or interacting with complex data structures.

Search for followup issues, regressions, and CVEs as well if you find a similar implementation.

## Available Tools

`gh` and the Sentry CLI should be availble. If either would be missing and would be useful, ask
that they be installed. https://cli.sentry.dev/

## Development environment (container only)

TODO: Setup containerized agent development. See sibling Stormbox repo
for an example, and "Development environment" in that AGENTs.md

### Container lifecycle

- Do **not** `docker stop` / `kill` / `pkill`  or
  anything it owns (vite on port 3000, ws-proxy inside it, etc.).
- If the container looks broken, ask first. Don't recreate it
  unilaterally.
- Port 3000 belongs to the container's vite. If something else is on
  port 3000 on the host, that's a configuration question for the user,
  not a license to kill the container.

## Vue and project layout (summary)

- `<script setup>` only; section order: script, template, style.
- Pinia stores in `src/stores/` (`defineStore` composition API, `*-store.js`).
- Routes in `src/router/`; human-readable folder names in URLs.
- Views in `src/views/`; shared components in `src/components/`.
- Config via `src/defines.js` and Vite env vars (`VITE_JMAP_SERVER_URL`, etc.).
- No native `<select>` in the product surface (constitution IX): its
  popup is unthemeable OS chrome. Menus and dropdowns reuse the app's
  styled patterns — e.g. the compose toolbar's `<details>` menus — so
  the same interaction always looks the same. Native chrome stays only
  where the platform UI is the feature (file and color pickers).

## Import conventions

Local module imports must be extensionless for `.ts` and `.js` sources;
keep `.vue` and other asset extensions explicit. This is enforced by
ESLint (`import-x/extensions`) and matches the convention used in the
`thunderbird-accounts` submodule.

```ts
// good
import { useMailStore } from '../stores/mail-store';
import MessageView from '../components/MessageView.vue';
import iconUrl from '../assets/icons/tb-folder-archive.svg?raw';

// bad
import { useMailStore } from '../stores/mail-store.js';
import { useMailStore } from '../stores/mail-store.ts';
```

Package imports (e.g. `@journeyapps/wa-sqlite/src/examples/IDBBatchAtomicVFS`)
follow the same rule — drop the runtime extension when the resolver can
infer it.

