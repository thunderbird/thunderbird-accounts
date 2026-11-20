# CI image publishing and promotion

`publish-images.yml` checks which image inputs changed on each push to `main`.
It builds the affected Accounts and Keycloak images on native amd64 and arm64
runners. `build-multiarch-image.yml` pushes each architecture to GHCR by digest,
then publishes the combined manifest under the commit SHA, `v<version>`, and
`latest`. A manual run on `main` rebuilds both images and updates the shared
tags without creating a draft release. A manual run on another ref skips both
image jobs if that ref includes the publish guard. A rebuild on `main` can
replace the SHA tag used by an existing draft.

After a successful push run publishes at least one image, `draft-release.yml`
creates a GitHub draft release pinned to that push commit. It assigns the next
`r-NNNN` number above existing releases and tags. When only one image changes,
promotion resolves the other image from the same commit's first-parent history.
Deleting an untagged draft can free its number for reuse.

The [Kargo Accounts project](https://kargo.pi.thunderbird.net/project/tb-accounts)
polls GHCR for the `latest` image pair and creates Freight from the two digests.
Freight promotes automatically to `tb-dev`. Once verified there, it is eligible
for automatic promotion to `tb-stage`. If a later build replaces either tag
before Kargo sees the pair, the draft can exist without matching Freight. Leave
that draft unpublished and coordinate with the Kargo operator.

Run `e2e-tests-browserstack-stage.yml` manually from GitHub Actions. The suite
tests the live stage endpoint. Check Kargo promotion history against the test
run times to confirm the matching Freight stayed current throughout the suite.
A new dispatch can replace one pending run while another is running.

Publish the draft after the matching Freight is verified in `tb-stage`.
`promote-release-to-tb-prod.yml` checks the release, both image digests, their
publishing history, and the matching Freight before requesting promotion to
`tb-prod`.

## Recovering a missing draft

In Actions, check both `publish-images` and `draft-release` for the intended
commit. A successful push with both image jobs skipped has no draft. If at
least one image merge job succeeded and the publish run concluded successfully,
rerun the draft job after resolving any transient error. This leaves the
published tags alone. If no draft workflow ran, for example because the publish
run predates this workflow, coordinate with the Kargo operator before retrying
the image build. A manually authored draft fails the production author check.

GitHub rejects the draft workflow's release request if the target SHA adds
or modifies workflow files relative to the current default branch. Rerunning
the draft job with the same target and branch state will fail again. Keep the
original target SHA and coordinate with the Kargo operator.

If an image failed to publish, a successful sibling may already have moved
`latest`, and Kargo may have rolled out that partial update. Before retrying
the publish run, check for newer runs. Retrying an older commit can move a
`latest` tag back. Confirm the exact pair is verified in `tb-stage` before
publishing a recovered draft.
