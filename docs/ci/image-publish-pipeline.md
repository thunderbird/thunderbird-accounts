# CI image publishing and promotion

`publish-images.yml` checks which image inputs changed on each push to `main`.
It builds the affected Accounts and Keycloak images on native amd64 and arm64
runners. `build-multiarch-image.yml` pushes each architecture to GHCR by digest,
then publishes the combined manifest under the commit SHA, `v<version>`, and
`latest`. A manual run rebuilds both images.

Kargo discovers the GHCR `latest` image pair as Freight and promotes it to
`tb-dev` and `tb-stage`. After a successful push run publishes at least one
image, `draft-release.yml` creates a GitHub draft release pinned to that push
commit. It assigns the next `r-NNNN` number above existing releases and tags.
When only one image changes, promotion resolves the other image from the same
commit's first-parent history.

Publish the draft after the matching Freight is verified in `tb-stage`.
`promote-release-to-tb-prod.yml` checks the release, both image digests, their
publishing history, and the matching Freight before requesting promotion to
`tb-prod`.

Run `e2e-tests-browserstack-stage.yml` from GitHub Actions after the expected
Freight reaches `tb-stage`. The suite tests the live stage endpoint.
