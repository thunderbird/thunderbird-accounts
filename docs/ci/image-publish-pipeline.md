# CI image pipelines

Two **independent** pipelines produce container images. They share no jobs, no
credentials, and no triggers beyond both reacting to `main`.

| Pipeline | Workflow | Registry | Arch | Purpose |
|---|---|---|---|---|
| **Deploy-stage** | `merge.yml` | ECR | amd64 only | Build + deploy to stage (ECS Fargate) via Pulumi |
| **Publish-images** | `publish-images.yml` + `build-multiarch-image.yml` | GHCR | amd64 + arm64 | Publish multi-arch manifest lists; no deploy |

## Publish-images (new, decoupled)

Native-runner split-arch build: each architecture builds on its own hardware
(no QEMU emulation) and pushes to GHCR by digest; a merge step stitches the
digests into one manifest list tagged `:<sha>`, `:v<version>`, and `:latest`.
Auth is the automatic `GITHUB_TOKEN` (`packages: write`) — no cloud credentials.

```mermaid
flowchart TD
    push["push to main / workflow_dispatch"] --> detect

    subgraph publish["publish-images.yml (GHCR, no deploy)"]
        detect["detect-changes (separate job)<br/>paths-filter + read version"]

        detect -->|accounts changed| acc
        detect -->|keycloak changed| kc

        subgraph acc["accounts → build-multiarch-image.yml"]
            direction TB
            a_amd["build amd64<br/>(ubuntu-latest)<br/>push by digest"]
            a_arm["build arm64<br/>(ubuntu-24.04-arm)<br/>push by digest"]
            a_merge["merge → manifest list<br/>:sha :vX.Y.Z :latest"]
            a_amd --> a_merge
            a_arm --> a_merge
        end

        subgraph kc["keycloak → build-multiarch-image.yml"]
            direction TB
            k_amd["build amd64<br/>(ubuntu-latest)<br/>push by digest"]
            k_arm["build arm64<br/>(ubuntu-24.04-arm)<br/>push by digest"]
            k_merge["merge → manifest list<br/>:sha :vX.Y.Z :latest"]
            k_amd --> k_merge
            k_arm --> k_merge
        end
    end

    a_merge --> ghcr[("GHCR<br/>ghcr.io/thunderbird/thunderbird-accounts{,-keycloak}")]
    k_merge --> ghcr
```

## Deploy-stage (unchanged, for contrast)

`merge.yml` still owns deployment: it builds the amd64 image, pushes to ECR,
and runs a single `pulumi up` to stage. It assumes the AWS deploy role via OIDC.

```mermaid
flowchart TD
    push2["push to main"] --> detect2["detect-changes"]
    detect2 --> build2["build amd64 image<br/>docker build --platform linux/amd64"]
    build2 --> ecr[("ECR")]
    build2 --> deploy["pulumi up → stage (ECS Fargate)"]
    deploy --> release["draft GitHub release<br/>(prod promotion)"]
```

## Why they're separate

- **Blast radius** — the GHCR publish holds no cloud credentials, so a branch or
  fork build can never assume the deploy role (the trust-boundary concern that
  killed running the deploy workflow off feature branches).
- **Independent cadence** — image publishing and stage deployment can evolve,
  fail, and be re-run without affecting each other.
- **Native multi-arch** — arm64 builds on real Graviton runners instead of QEMU
  emulation, so they're faster and not subject to emulation miscompiles.
