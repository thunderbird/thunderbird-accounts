#!/usr/bin/env bash
set -euo pipefail

lookup="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/find-release-pair.sh"
scratch=$(mktemp -d)
trap 'find "$scratch" -depth -delete' EXIT
cd "$scratch"

git init -q -b main
git config user.name pair-record-test
git config user.email pair-record-test
git config commit.gpgsign false

commit() {
  git commit -q --allow-empty -m "$1"
  git rev-parse HEAD
}

expect_failure() {
  local release=$1 message=$2 actual
  if actual=$(bash "$lookup" "$release" 2>&1) || [[ "$actual" != *"$message"* ]]; then
    printf 'Expected failure containing %s, got %s\n' "$message" "$actual" >&2
    exit 1
  fi
}

expect_pair() {
  local release=$1 record=$2 accounts=$3 keycloak=$4 actual expected
  expected=$(printf '%s\t%s\t%s' "$record" "$accounts" "$keycloak")
  actual=$(bash "$lookup" "$release")
  if [[ "$actual" != "$expected" ]]; then
    printf 'Expected %s, got %s\n' "$expected" "$actual" >&2
    exit 1
  fi
}

write_pair() {
  local release=$1 accounts=$2 keycloak=$3 run=$4
  cat > pair.yaml <<EOF
revision: "$release"
version: 1.0.0
run: $run
accounts:
  image: ghcr.io/thunderbird/thunderbird-accounts
  digest: $accounts
  revision: "$first_release"
keycloak:
  image: ghcr.io/thunderbird/thunderbird-accounts-keycloak
  digest: $keycloak
  revision: "$never_published"
EOF
  git add pair.yaml
}

first_release=$(commit 'First release')
second_release=$(commit 'Second release')
never_published=$(commit 'No pair record')
expect_failure "$first_release" 'branch kargo/accounts-pairs was not found'

git switch -q --orphan kargo/accounts-pairs
printf -v first_digest 'sha256:%064d' 1
printf -v second_digest 'sha256:%064d' 2
printf -v rebuilt_digest 'sha256:%064d' 3

write_pair "$first_release" "$first_digest" "$first_digest" 1
first_record=$(commit 'First record')
git update-ref refs/remotes/origin/kargo/accounts-pairs "$first_record"
expect_pair "$first_release" "$first_record" "$first_digest" "$first_digest"

write_pair "$first_release" "$rebuilt_digest" "$first_digest" 1
commit 'Rebuilt first record' > /dev/null
rebuilt_record=$(commit 'Repeat the rebuilt first record with the same tree')
write_pair "$second_release" "$rebuilt_digest" "$second_digest" 2
second_record=$(commit 'Second record')
git update-ref refs/remotes/origin/kargo/accounts-pairs "$second_record"
expect_pair "$first_release" "$rebuilt_record" "$rebuilt_digest" "$first_digest"
expect_pair "$second_release" "$second_record" "$rebuilt_digest" "$second_digest"
expect_failure "$never_published" "no pair.yaml on kargo/accounts-pairs has revision $never_published"

write_pair "$second_release" "$rebuilt_digest" invalid 3
invalid_record=$(commit 'Invalid record')
git update-ref refs/remotes/origin/kargo/accounts-pairs "$invalid_record"
expect_failure "$second_release" "bad Keycloak digest in pair.yaml at $invalid_record"

printf '%s\n' 'Release pair lookup passed.'
