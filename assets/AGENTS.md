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


## Patterns

### Guard against double-click to delete

Users may double-click on delete actions, causing the second request to return a resource not found error. On the frontend, disable the submit button while a delete request is in progress to avoid
the second request from being sent.

## Accessability

Accessbility best practices must be followed, and any compromises surfaced to the user.
