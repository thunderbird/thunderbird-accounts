## Vue layout (summary)

- `<script setup>` only; section order: script, template, style.

## Import conventions

Local module imports must be extensionless for `.ts` and `.js` sources;
keep `.vue` and other asset extensions explicit. This is enforced by
ESLint (`import-x/extensions`)

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

## Zeplin

- Match Zeplin designs to the pixel.
- Zeplin MCP server should be available. Ask to have one installed if missing for Zeplin work.

## Patterns

### Validation

 - Rely on backend validation errors instead of duplicating validation client-side

### Types

 - Types go in `types.ts` files

### Strings

 - All user-facing text lives in the locale file. Formatters take the user's locale and never hard-code one or a 12-hour clock.

### Guard against double-click to delete

Users may double-click on delete actions, causing the second request to return a resource not found error. On the frontend, disable the submit button while a delete request is in progress to avoid
the second request from being sent.

## Accessability

Accessbility best practices must be followed, and any compromises surfaced to the user.

 - `<router-link>` for navigation
 - aria-label on decorative icons
 - `<time>` for dates
 - check contrast

## Shared functionality

 - A sibling project `services-ui` is used to house shared Vue components. It is likely checked
out in a sibling repo.
 - check the services-ui Storybook before writing a component or styling a button, modal, or divider.
