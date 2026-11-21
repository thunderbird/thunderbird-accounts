#!/usr/bin/env bash
set -euo pipefail

release_sha=$1
branch=kargo/accounts-pairs
ref="refs/remotes/origin/$branch"

fail() {
  printf '%s\n' "$*" >&2
  exit 1
}

git show-ref --verify --quiet "$ref" || fail "branch $branch was not found"
commits=$(git rev-list --first-parent "$ref") || fail "could not read the history of $branch"

while read -r commit; do
  fields=$(git show "$commit:pair.yaml" | yq -er '[.revision, .accounts.digest, .keycloak.digest] | @tsv') \
    || fail "could not read pair.yaml at $commit on $branch"
  IFS=$'\t' read -r revision accounts_digest keycloak_digest <<< "$fields"
  [[ "$revision" == "$release_sha" ]] || continue
  [[ "$accounts_digest" =~ ^sha256:[0-9a-f]{64}$ ]] || fail "bad Accounts digest in pair.yaml at $commit"
  [[ "$keycloak_digest" =~ ^sha256:[0-9a-f]{64}$ ]] || fail "bad Keycloak digest in pair.yaml at $commit"
  printf '%s\t%s\t%s\n' "$commit" "$accounts_digest" "$keycloak_digest"
  exit 0
done <<< "$commits"

fail "no pair.yaml on $branch has revision $release_sha"
