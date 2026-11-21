set -euo pipefail

fail() {
  echo "Cannot publish image pair: $*" >&2
  exit 1
}

sha_pattern='^[0-9a-f]{40}$'
digest_pattern='^sha256:[0-9a-f]{64}$'
record_ref=refs/heads/kargo/accounts-pairs
accounts_image=ghcr.io/thunderbird/thunderbird-accounts
keycloak_image=ghcr.io/thunderbird/thunderbird-accounts-keycloak

[[ "$GITHUB_SHA" =~ $sha_pattern ]] || fail "invalid source revision"
[[ "$VERSION" =~ ^[0-9][0-9a-zA-Z._-]*$ ]] || fail "invalid version"
[[ "$GITHUB_RUN_NUMBER" =~ ^[1-9][0-9]*$ ]] || fail "invalid run number"
case "$ACCOUNTS_RESULT:$KEYCLOAK_RESULT:$SEED_PAIR" in
  success:success:false|success:skipped:false|skipped:success:false|skipped:skipped:true) ;;
  *) fail "expected a successful build with no failed sibling, or a seed with both builds skipped" ;;
esac

parent=
previous=
if git ls-remote --exit-code --heads origin "$record_ref" > /dev/null; then
  git fetch --no-tags origin "$record_ref"
  parent=$(git rev-parse FETCH_HEAD)
  [[ "$(git ls-tree --name-only "$parent")" == pair.yaml ]] || fail "branch must contain only pair.yaml"
  previous=$(git show "$parent:pair.yaml" | yq -o=json '.')
  previous_revision=$(jq -er '.revision' <<< "$previous")
  [[ "$previous_revision" =~ $sha_pattern ]] || fail "invalid revision in current pair.yaml"
  git merge-base --is-ancestor "$previous_revision" "$GITHUB_SHA" ||
    fail "current record revision $previous_revision is not an ancestor of $GITHUB_SHA"
else
  [[ $? == 2 ]] || fail "could not check the remote record branch"
fi

resolve_image() {
  local key=$1 image=$2 result=$3 digest=$4 revision=$GITHUB_SHA fields
  if [[ "$result" == skipped ]]; then
    if [[ "$SEED_PAIR" == true || -z "$parent" ]]; then
      fields=$(docker buildx imagetools inspect --format '{{json .Manifest}}' "$image:latest" |
        jq -er 'select(.mediaType == "application/vnd.oci.image.index.v1+json") |
          [.digest, .annotations["org.opencontainers.image.revision"]] | @tsv') ||
        fail "could not read the OCI index for $image:latest"
    else
      fields=$(jq -er --arg key "$key" --arg image "$image" \
        '.[$key] | select(.image == $image) | [.digest, .revision] | @tsv' <<< "$previous") ||
        fail "could not read $image from the current pair.yaml"
    fi
    IFS=$'\t' read -r digest revision <<< "$fields"
  fi
  [[ "$digest" =~ $digest_pattern ]] || fail "invalid index digest for $image"
  [[ "$revision" =~ $sha_pattern ]] || fail "invalid image revision for $image"
  printf '%s %s\n' "$digest" "$revision"
}

accounts=$(resolve_image accounts "$accounts_image" "$ACCOUNTS_RESULT" "${ACCOUNTS_DIGEST-}")
keycloak=$(resolve_image keycloak "$keycloak_image" "$KEYCLOAK_RESULT" "${KEYCLOAK_DIGEST-}")
read -r accounts_digest accounts_revision <<< "$accounts"
read -r keycloak_digest keycloak_revision <<< "$keycloak"

record=$(cat <<EOF
revision: "$GITHUB_SHA"
version: "$VERSION"
run: $GITHUB_RUN_NUMBER
accounts:
  image: $accounts_image
  digest: $accounts_digest
  revision: "$accounts_revision"
keycloak:
  image: $keycloak_image
  digest: $keycloak_digest
  revision: "$keycloak_revision"
EOF
)

if [[ "$SEED_PAIR" == true && -n "$parent" ]]; then
  existing=$(jq -cS '.' <<< "$previous")
  candidate=$(yq -o=json '.' <<< "$record" | jq -cS '.')
  [[ "$candidate" == "$existing" ]] || fail "the branch already has a different record"
  echo "The branch already has this record."
  exit 0
fi

subject="v$VERSION ${GITHUB_SHA:0:7} accounts=${accounts_digest:7:12} keycloak=${keycloak_digest:7:12}"
(( ${#subject} <= 72 )) || fail "record commit subject exceeds 72 characters"
blob=$(printf '%s\n' "$record" | git hash-object -w --stdin)
tree=$(printf '100644 blob %s\tpair.yaml\n' "$blob" | git mktree)
parents=()
if [[ -n "$parent" ]]; then
  parents=(-p "$parent")
fi
commit=$(git -c user.name='GitHub Actions' -c user.email=github-actions -c commit.gpgsign=false \
  commit-tree "$tree" "${parents[@]}" -m "$subject")
git push origin "$commit:$record_ref"
