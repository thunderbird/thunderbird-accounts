# CI image publishing and promotion

`publish-images.yml` checks which image inputs changed on each push to `main`.
It builds the affected Accounts and Keycloak images on native amd64 and arm64
runners. `build-multiarch-image.yml` pushes each architecture to GHCR by digest,
then publishes the combined manifest under the commit SHA, `v<version>`, and
`latest`. A manual run rebuilds both images and updates `latest` without
creating a draft release.

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

Run `e2e-tests-browserstack-stage.yml` manually from GitHub Actions while the
matching Freight is current in `tb-stage`. The suite tests the live stage
endpoint.

Publish the draft after the matching Freight is verified in `tb-stage`.
`promote-release-to-tb-prod.yml` checks the release, both image digests, their
publishing history, and the matching Freight before requesting promotion to
`tb-prod`.

## Recovering a missing draft

In Actions, check both `publish-images` and `draft-release` for the intended
commit. If an image merge job succeeded in a successful publish run, resolve
the draft error and rerun the failed draft job. This leaves the published
tags alone. A run with both image jobs skipped has no draft.

GitHub can reject release creation for an older target whose workflow files
differ from the current default branch. If this happens, keep the original
target SHA and coordinate with the Kargo operator on the release.

If an image failed to publish, a successful sibling may already have moved
`latest`, and Kargo may have rolled out that partial update. Before retrying
the publish run, check for newer runs. Retrying an older commit can move a
`latest` tag back. Confirm the exact pair is verified in `tb-stage` before
publishing a recovered draft.
