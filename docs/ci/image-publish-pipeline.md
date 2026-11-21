# CI image publishing and promotion

`publish-images.yml` checks which image inputs changed on each push to `main`.
It builds the affected Accounts and Keycloak images on native amd64 and arm64
runners. `build-multiarch-image.yml` pushes each architecture to GHCR by digest,
then publishes the multi-architecture index under the commit SHA, `v<version>`,
and `latest`. A regular manual run rebuilds both images from the selected ref
and updates the shared tags. Manual runs do not create draft releases.

## Record the image pair

On `main`, the **Record image pair** job waits for all selected image jobs to
succeed. If at least one image was built, it commits `pair.yaml` to the
`kargo/accounts-pairs` branch. That branch contains only `pair.yaml` and advances
by fast-forward. The record's top-level `revision` is the `main` commit that ran
the workflow. `version` comes from `pyproject.toml` without the `v` prefix, and
`run` is the `publish-images` run number. The `accounts` and `keycloak` entries
each hold the GHCR repository in `image`, its `sha256:` multi-architecture
index `digest`, and the source commit in `revision`.

For each image built in the run, the job uses the index digest reported by GHCR
after the push. A skipped image keeps the digest and source revision from the
previous record. If the branch is missing, the job reads the skipped image's
`latest` index digest and its `org.opencontainers.image.revision` annotation
from GHCR.

After a successful push run records a pair, `draft-release.yml` creates a
GitHub draft release pinned to that push commit. It assigns the next `r-NNNN`
number above existing releases and tags. Deleting an untagged draft can free
its number for reuse.

## Seed the first record

In GitHub Actions, run `publish-images` on `main` with `seed_pair` enabled.
The run skips both image builds and reads the two current GHCR `latest` indexes.
Check that `kargo/accounts-pairs` contains `pair.yaml` with both index digests
and source revisions before switching the Kargo Warehouse to the branch. The
seed creates no draft release. Once a record exists, seeding can only succeed
as a no-op when the candidate record is identical, including its run number.

## Verify and promote

The `accounts-pair` Warehouse in the Kargo Accounts project watches
`kargo/accounts-pairs` and creates Freight from the record commit. Promotions
use both digests from that commit's `pair.yaml`. Freight promotes automatically
to `tb-dev`. Once verified there, it is eligible for automatic promotion to
`tb-stage`. [Kargo Accounts project](https://kargo.pi.thunderbird.net/project/tb-accounts)

Run `e2e-tests-browserstack-stage.yml` manually from GitHub Actions. The suite
tests the live stage endpoint. Check Kargo promotion history against the test
run times to confirm the matching Freight stayed current throughout the suite.
A new dispatch can replace one pending run while another is running.

Publish the draft after the matching Freight is verified in `tb-stage`.
`promote-release-to-tb-prod.yml` finds the newest record whose top-level
`revision` matches the pinned release commit. It requires exactly one Freight
in `tb-accounts` carrying that record commit and waits for it to be verified in
`tb-stage` before requesting promotion to `tb-prod`. If there is no matching
record or verified Freight, leave the draft unpublished and coordinate with
the Kargo operator. GitHub runs the workflow from the tagged release commit.
Releases pinned to commits before the record lookup was introduced still use
the image-digest lookup. [Release event reference](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#release)
[Workflow execution reference](https://docs.github.com/en/actions/concepts/workflows-and-actions/workflows)

## Recover a failed publish or a missing draft

In Actions, check both `publish-images` and `draft-release` for the intended
commit. A failed or cancelled image job leaves the previous record in place
even if its sibling already moved a GHCR tag. Resolve the failure and rerun
`publish-images` for that commit. If the fix requires a source change, publish
the fix on `main`. Check for newer runs before retrying, since an old build can
move shared tags back even if its record write is refused. A rerun for the same
commit may write a new record. Confirm Freight for the newest matching record
is verified in `tb-stage` before publishing the draft.

A successful push that built neither image creates no record or draft. If
the push wrote a record and the draft workflow failed, rerun the draft workflow
after resolving the error. If no draft workflow ran, coordinate with the Kargo
operator before retrying the image build. A manually authored draft fails the
production author check.

GitHub rejects the draft workflow's release request if the target SHA adds
or modifies workflow files relative to the current default branch. Rerunning
the draft job with the same target and branch state will fail again. Keep the
original target SHA and coordinate with the Kargo operator.
