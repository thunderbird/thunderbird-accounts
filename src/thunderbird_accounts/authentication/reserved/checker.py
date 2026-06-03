import json
import re
import unicodedata
from pathlib import Path

# ---------------------------------------------------------------------------
# tbpro-specific combinatorial patterns (brands + teams), matched by regex.
#
# These are brand x token and team x suffix combinations that do not map cleanly
# to the exact/affix word lists, so they stay here. Plain reserved words live in
# the JSON files instead (see README.md).
# ---------------------------------------------------------------------------

# brand related names, and also help/support
brands = '(thunderbird|tbpro|thundermail|thunderbirdpro|mzla|mozilla|firefox)?'

# Brand names plus common tokens
names_with_brands = [
    brands + '?',
    brands + '[_|-]?admin?',
    brands + '[_|-]?support?',
    brands + '[_|-]?customer[_|-]?support?',
    brands + '[_|-]?help?',
    brands + '[_|-]?customer[_|-]?help?',
    brands + '[_|-]?mozilla?',
    brands + '[_|-]?email?',
    brands + '[_|-]?org?',
]
reserved_names = [n + '$' for n in names_with_brands]

# official/real versions
reserved_names = (
    reserved_names
    + ['official[_|-]?' + n for n in names_with_brands]
    + [n + '[_|-]?official$' for n in names_with_brands]
    + ['real[_|-]?' + n for n in names_with_brands]
    + [n + '[_|-]?real$' for n in names_with_brands]
)

# potential company team use. Base names are also covered by generated-words.json;
# the team/_team suffix combinations are the combinatorial part kept here.
teams = [
    'team(s)*',
    'hr',
    'accounts',
    'engineering',
    'marketing',
    'design',
    'legal',
    'privacy',
    'policy',
    'finance',
    'sales',
]
reserved_names += ['^' + n + '(team|_team)*$' for n in teams]

regexes = [re.compile('^' + n) for n in reserved_names]


# ---------------------------------------------------------------------------
# Reserved-word lists (see README.md and THIRD_PARTY_LICENSES):
#   * generated-words.json -- generated from upstream sources by update.py, with
#     two disjoint sections, "exact" and "affix".
#   * exact-words.json / affix-words.json -- hand-maintained tbpro additions.
#
# "exact" entries match only when the local-part equals an entry; "affix" entries
# also match as a prefix or suffix (e.g. "admin-billing", "company-postmaster").
# Entries include Unicode homograph variants; input is NFKC-normalized and
# lowercased before lookup.
# ---------------------------------------------------------------------------
_DATA_DIR = Path(__file__).resolve().parent
_GENERATED_WORDS_FILE = 'generated-words.json'
_EXACT_WORDS_FILE = 'exact-words.json'
_AFFIX_WORDS_FILE = 'affix-words.json'


def _normalize_local_part(value: str) -> str:
    """Normalize an email local-part for reserved-name comparison.

    NFKC folding collapses fullwidth/compatibility characters to their ASCII
    forms; the lists carry the remaining (Cyrillic/Greek) homograph variants so
    they are still matched exactly.
    """
    return unicodedata.normalize('NFKC', value).strip().lower()


def _read_json(filename: str):
    with open(_DATA_DIR / filename, encoding='utf-8') as fh:
        return json.load(fh)


def _normalized(words) -> set[str]:
    names = {_normalize_local_part(word) for word in words}
    names.discard('')
    return names


def _load_words() -> tuple[frozenset[str], frozenset[str]]:
    generated = _read_json(_GENERATED_WORDS_FILE)
    exact = _normalized(generated['exact']) | _normalized(_read_json(_EXACT_WORDS_FILE))
    affix = _normalized(generated['affix']) | _normalized(_read_json(_AFFIX_WORDS_FILE))
    return frozenset(exact), frozenset(affix)


# RESERVED_LOCAL_PARTS is matched by exact comparison only;
# AFFIX_RESERVED_LOCAL_PARTS is matched by exact comparison, prefix, or suffix.
RESERVED_LOCAL_PARTS, AFFIX_RESERVED_LOCAL_PARTS = _load_words()


def is_reserved(test_string: str) -> bool:
    """Checks the address or random string is a reserved name which should fail user or alias creation if so."""
    local_part = _normalize_local_part(test_string)

    if local_part:
        # Exact match against the exact word lists.
        if local_part in RESERVED_LOCAL_PARTS:
            return True

        # Exact / prefix / suffix match against the affix word lists.
        if any(
            local_part == term or local_part.startswith(term) or local_part.endswith(term)
            for term in AFFIX_RESERVED_LOCAL_PARTS
        ):
            return True

    # tbpro brand / team combinatorial patterns (matched against raw input).
    return any(r.match(test_string) for r in regexes)
