set -euo pipefail

publisher="$(cd "$(dirname "$0")" && pwd)/publish-image-pair.sh"
scratch=$(mktemp -d)
trap 'find "$scratch" -depth -delete' EXIT

git init --bare --quiet "$scratch/remote"
git init --initial-branch=main --quiet "$scratch/work"
cd "$scratch/work"
git remote add origin "$scratch/remote"
git config user.name Test
git config user.email test
git config commit.gpgsign false

revision() {
  git commit --quiet --allow-empty -m "$1"
  git rev-parse HEAD
}

original=$(revision original)
first=$(revision first)
paired=$(revision paired)
accounts_only=$(revision accounts-only)
keycloak_only=$(revision keycloak-only)
git push --quiet origin main

printf -v accounts_latest 'sha256:%064d' 1
printf -v keycloak_latest 'sha256:%064d' 2
printf -v accounts_first 'sha256:%064d' 3
printf -v accounts_paired 'sha256:%064d' 4
printf -v keycloak_paired 'sha256:%064d' 5
printf -v accounts_new 'sha256:%064d' 6
printf -v keycloak_new 'sha256:%064d' 7

docker() {
  [[ "$#" == 6 && "$1 $2 $3 $4 $5" == 'buildx imagetools inspect --format {{json .Manifest}}' ]]
  local digest
  case "$6" in
    ghcr.io/thunderbird/thunderbird-accounts:latest) digest=$MOCK_ACCOUNTS_LATEST ;;
    ghcr.io/thunderbird/thunderbird-accounts-keycloak:latest) digest=$MOCK_KEYCLOAK_LATEST ;;
    *) return 1 ;;
  esac
  jq -nc --arg digest "$digest" --arg revision "$MOCK_REVISION" \
    '{mediaType: "application/vnd.oci.image.index.v1+json", digest: $digest,
      annotations: {"org.opencontainers.image.revision": $revision}}'
}
export -f docker

publish() {
  GITHUB_SHA=$1 GITHUB_RUN_NUMBER=$2 VERSION=1.24.2 SEED_PAIR=$3 \
    ACCOUNTS_RESULT=$4 ACCOUNTS_DIGEST=$5 KEYCLOAK_RESULT=$6 KEYCLOAK_DIGEST=$7 \
    bash "$publisher"
}

record_ref=refs/heads/kargo/accounts-pairs
record_head() {
  git --git-dir="$scratch/remote" rev-parse "$record_ref"
}

verify_record() {
  local head
  head=$(record_head)
  [[ "$(git ls-tree --name-only "$head")" == pair.yaml ]]
  git show "$head:pair.yaml" | yq -o=json '.' |
    jq -e --arg rev "$1" --argjson run "$2" --arg ad "$3" --arg ar "$4" --arg kd "$5" --arg kr "$6" \
      '. == {revision: $rev, version: "1.24.2", run: $run,
        accounts: {image: "ghcr.io/thunderbird/thunderbird-accounts", digest: $ad, revision: $ar},
        keycloak: {image: "ghcr.io/thunderbird/thunderbird-accounts-keycloak", digest: $kd, revision: $kr}}' > /dev/null
  [[ "$(git log -1 --format=%s "$head")" == "v1.24.2 ${1:0:7} accounts=${3:7:12} keycloak=${5:7:12}" ]]
}

assert_refused() {
  local before diagnostic=$1
  shift
  before=$(record_head)
  if publish "$@" > "$scratch/result" 2>&1; then
    echo "Expected refusal: $diagnostic" >&2
    exit 1
  fi
  if ! grep -Fq "$diagnostic" "$scratch/result"; then
    cat "$scratch/result" >&2
    exit 1
  fi
  [[ "$(record_head)" == "$before" ]]
}

export MOCK_ACCOUNTS_LATEST=$accounts_latest MOCK_KEYCLOAK_LATEST=$keycloak_latest MOCK_REVISION=$original
publish "$first" 1 false success "$accounts_first" skipped ''
verify_record "$first" 1 "$accounts_first" "$first" "$keycloak_latest" "$original"
[[ "$(git rev-list --count "$(record_head)")" == 1 ]]
unset MOCK_ACCOUNTS_LATEST MOCK_KEYCLOAK_LATEST MOCK_REVISION

publish "$paired" 2 false success "$accounts_paired" success "$keycloak_paired"
verify_record "$paired" 2 "$accounts_paired" "$paired" "$keycloak_paired" "$paired"
publish "$accounts_only" 3 false success "$accounts_new" skipped ''
verify_record "$accounts_only" 3 "$accounts_new" "$accounts_only" "$keycloak_paired" "$paired"
publish "$keycloak_only" 4 false skipped '' success "$keycloak_new"
verify_record "$keycloak_only" 4 "$accounts_new" "$accounts_only" "$keycloak_new" "$keycloak_only"

assert_refused 'is not an ancestor' "$paired" 2 false success "$accounts_paired" success "$keycloak_paired"
previous=$(record_head)
publish "$keycloak_only" 4 false skipped '' success "$keycloak_new"
[[ "$(git rev-parse "$(record_head)^")" == "$previous" ]]
verify_record "$keycloak_only" 4 "$accounts_new" "$accounts_only" "$keycloak_new" "$keycloak_only"
assert_refused 'no failed sibling' "$keycloak_only" 5 false success "$accounts_new" failure ''
assert_refused 'no failed sibling' "$keycloak_only" 5 false cancelled '' success "$keycloak_new"
assert_refused 'expected a successful build' "$keycloak_only" 5 false skipped '' skipped ''
assert_refused 'invalid index digest' "$keycloak_only" 5 false success '' skipped ''

git --git-dir="$scratch/remote" update-ref -d "$record_ref"
export MOCK_ACCOUNTS_LATEST=$accounts_latest MOCK_KEYCLOAK_LATEST=$keycloak_latest MOCK_REVISION=$original
publish "$keycloak_only" 6 true skipped '' skipped ''
verify_record "$keycloak_only" 6 "$accounts_latest" "$original" "$keycloak_latest" "$original"
seed=$(record_head)
[[ "$(git rev-list --count "$seed")" == 1 ]]
publish "$keycloak_only" 6 true skipped '' skipped ''
[[ "$(record_head)" == "$seed" ]]
assert_refused 'already has a different record' "$keycloak_only" 7 true skipped '' skipped ''

echo 'Image pair publishing tests passed.'
