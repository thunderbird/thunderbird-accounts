#!/usr/bin/env python3
"""Rebuild the reserved local-part lists from their upstream sources.

Fetches the upstream projects, normalizes and de-duplicates their entries, and
writes `generated-words.json` with two sections:

    "exact" -- reserved only when the local-part equals an entry
    "affix" -- reserved when the local-part equals, starts with, or ends with an
               entry

The two sections are kept disjoint (an affix entry already covers its own exact
match). This file is generated; do not edit it by hand -- add hand-maintained
words to exact-words.json / affix-words.json instead. Run:

    uv run python src/thunderbird_accounts/authentication/reserved/update.py

After running, bump the "Retrieved" dates in README.md and re-run the
authentication tests. License notices live in THIRD_PARTY_LICENSES (maintained
by hand); update it if an upstream copyright or license ever changes.
"""

import json
import unicodedata
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Generated file: a "_warning" note plus two keyed sections ("exact", "affix").
GENERATED_WORDS_FILE = 'generated-words.json'
GENERATED_WARNING = (
    'GENERATED FILE -- do not edit by hand. Regenerate with update.py. '
    'Add hand-maintained words to exact-words.json or affix-words.json instead.'
)

# Forward Email -- reserved-email-addresses-list (MIT)
FORWARD_EMAIL_RAW = 'https://raw.githubusercontent.com/forwardemail/reserved-email-addresses-list/master'
FORWARD_EMAIL_EXACT_FILES = ('index.json',)
FORWARD_EMAIL_AFFIX_FILES = ('admin-list.json', 'no-reply-list.json')

# shouldbee -- reserved-usernames (MIT), exact match
SHOULDBEE_RAW = 'https://raw.githubusercontent.com/shouldbee/reserved-usernames/master'

# miketromba -- reserved-slugs (MIT), exact match. Merge every category except the
# ones that over-block legitimate addresses or are out of scope for this check.
RESERVED_SLUGS_RAW = 'https://raw.githubusercontent.com/miketromba/reserved-slugs/main'
RESERVED_SLUGS_CATEGORIES = (
    'ai-ml',
    'api-developer',
    'app-routes',
    'auth',
    'dns-mail',
    'ecommerce',
    'financial',
    'health-monitoring',
    'impersonation',
    'infrastructure',
    'legal',
    'media-streaming',
    'protocol-tech',
    'saas',
    'seo-marketing',
    'social',
    'well-known-paths',
)
RESERVED_SLUGS_EXCLUDED = ('country-codes', 'languages', 'profanity')

# Affix stems that are too short/common for prefix+suffix matching -- as an affix
# they over-block legitimate local-parts (e.g. "mail" -> gmail/mailbox,
# "dev" -> developer, "test" -> latest). They (and their homograph/leet variants)
# are kept reserved but demoted to exact-match only.
AFFIX_DEMOTED_TO_EXACT = (
    'dev',
    'finance',
    'hr',
    'info',
    'mail',
    'pop',
    'sales',
    'test',
)

# ASCII letter -> the characters that look like it (homograph / leet). Used so a
# demoted stem also demotes every look-alike spelling of it, not just the ASCII
# form (e.g. "pop" also demotes "p0p", "pοp", "pор").
_CONFUSABLES = {
    'a': {'a', '\u0251', '\u03b1', '\u0430', '\u2c65'},
    'c': {'c', '\u0441'},
    'e': {'e', '\u03b5', '\u0435'},
    'h': {'h', '\u04bb'},
    'i': {'i', '1', '\u03b9', '\u0456'},
    'l': {'l', '1'},
    'n': {'n', '\u03b7'},
    'o': {'o', '0', '\u03bf', '\u043e'},
    'p': {'p', '\u03c1', '\u0440'},
    'r': {'r', '\u0433'},
    's': {'s', '\u03c2', '\u03c3', '\u0455'},
}


def _normalize(value: str) -> str:
    # Keep in sync with checker._normalize_local_part.
    return unicodedata.normalize('NFKC', value).strip().lower()


def _is_confusable(candidate: str, stem: str) -> bool:
    """True if candidate is stem with zero or more letters swapped for look-alikes."""
    if len(candidate) != len(stem):
        return False
    return all(char in _CONFUSABLES.get(stem_char, {stem_char}) for stem_char, char in zip(stem, candidate))


def _fetch_json(url: str) -> list[str]:
    with urllib.request.urlopen(url) as response:
        return json.load(response)


def _fetch_lines(url: str) -> list[str]:
    with urllib.request.urlopen(url) as response:
        return response.read().decode('utf-8').splitlines()


def _write_words(exact: set[str], affix: set[str]) -> None:
    payload = {'_warning': GENERATED_WARNING, 'exact': sorted(exact), 'affix': sorted(affix)}
    with open(HERE / GENERATED_WORDS_FILE, 'w', encoding='utf-8') as fh:
        json.dump(payload, fh, indent='\t', ensure_ascii=False)
        fh.write('\n')


def _reserved_slug_entries() -> set[str]:
    entries: set[str] = set()
    for category in RESERVED_SLUGS_CATEGORIES:
        entries.update(_fetch_json(f'{RESERVED_SLUGS_RAW}/data/categories/{category}/slugs.json'))
    return entries


def main() -> None:
    exact: set[str] = set()
    for filename in FORWARD_EMAIL_EXACT_FILES:
        exact.update(_fetch_json(f'{FORWARD_EMAIL_RAW}/{filename}'))
    exact.update(_fetch_lines(f'{SHOULDBEE_RAW}/reserved-usernames.txt'))
    exact.update(_reserved_slug_entries())

    affix: set[str] = set()
    for filename in FORWARD_EMAIL_AFFIX_FILES:
        affix.update(_fetch_json(f'{FORWARD_EMAIL_RAW}/{filename}'))

    affix = {_normalize(name) for name in affix} - {''}
    exact = {_normalize(name) for name in exact} - {''}

    # Demote over-broad affix stems (and their look-alike variants) to exact-only.
    demoted_stems = [_normalize(name) for name in AFFIX_DEMOTED_TO_EXACT]
    moved = {term for term in affix if any(_is_confusable(term, stem) for stem in demoted_stems)}
    exact |= moved
    affix -= moved

    # An affix entry already matches its own exact form, so keep the sections disjoint.
    exact -= affix

    _write_words(exact, affix)
    print(f'{GENERATED_WORDS_FILE}: {len(exact)} exact + {len(affix)} affix entries')
    print(f'(reserved-slugs excluded categories: {", ".join(RESERVED_SLUGS_EXCLUDED)})')
    print('Done. Bump the README "Retrieved" dates and re-run the authentication tests.')


if __name__ == '__main__':
    main()
