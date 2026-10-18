# Provider secret handling

Jev Engineering v1.7 never ships provider credentials inside source, wheels, ZIPs, YAML configs, logs, or evidence artifacts.

## Local / Hermes

Preferred sources, in order:

1. process environment (`TYPESAFE_API_KEY`, `DIALAGRAM_API_KEY`),
2. an explicitly supplied untracked dotenv (`jev-one ... --env-file <path>`),
3. Hermes profile dotenv, loaded explicitly by the existing `--hermes-profile` path.

`HERMES_CUSTOM_DIALAGRAM_ME_API_KEY` and `NEXUM_API_KEY` map to the canonical `DIALAGRAM_API_KEY` name.

Use `jev-one secret-status` to verify presence without printing values. `--fingerprint` emits only a short SHA-256 correlation fingerprint.

## GitHub Actions

Use GitHub **Actions secrets**, not repository variables. Recommended names:

- `TYPESAFE_API_KEY`
- `DIALAGRAM_API_KEY`

The bundled `.github/workflows/live-provider-smoke.yml` references those secret names and injects them only into the provider smoke job.

For stronger isolation, configure them as **environment secrets** in a GitHub environment named `provider-smoke`; optionally require reviewer approval for that environment. The workflow is manual-only (`workflow_dispatch`) so a normal push or pull request cannot consume the provider credentials.

Repository/organization/environment secret creation is an administrative control-plane action and is intentionally not encoded in the repository. The repository contains only secret names and wiring.

## Release invariant

A release is invalid if a known provider-secret pattern is present in tracked/release files. `scripts/verify_no_secrets.py` is included in the verification gate and CI.

### CLI installation helper

On an authenticated workstation with GitHub CLI:

```bash
export TYPESAFE_API_KEY='...'
export DIALAGRAM_API_KEY='...'
./scripts/install_github_secrets.sh OWNER/REPO provider-smoke
unset TYPESAFE_API_KEY DIALAGRAM_API_KEY
```

The helper creates/updates the GitHub environment and pipes values to `gh secret set` through standard input. It does not place the values on the `gh` command line or write them to repository files.

## v1.7 receipt-signing keys

`ReceiptSigner` also consumes runtime-supplied HMAC key material. Keep receipt-signing keys outside model context and source control. A recommended production secret name is `AFTERGRAPH_RECEIPT_HMAC_KEY`; the reference library accepts raw key bytes from the caller and does not automatically persist them. Rotate provider and receipt keys independently.
