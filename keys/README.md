# Owner ceremony: rooting the owner-authority proxy

This directory holds the **root of trust** for the owner-authority agent
(spec: `docs/superpowers/specs/2026-09-20-owner-authority-agent-design.md`).
Three files must exist here before the spine will sign anything:

| File | What it is | Who produces it |
|------|------------|-----------------|
| `delegation_record.json` | The mandate's terms (scope, reserved list, expiry, budget ceiling, bindings) | Owner reviews/edits the committed draft, then signs it |
| `delegation_record.sig` | Detached GPG signature over the record | **Owner only, via the hardware token** |
| `owner.pub.asc` | The owner's armored public key | Exported from the token, committed |

The private key **never** enters this repo and **never** enters this machine's
filesystem in software form. The agent can verify `delegation_record.sig` against
`owner.pub.asc` on every signing act, but can never produce one — that is the whole
design (spec §1, decisions 2 + 5).

`delegation_record.json` is committed **unsigned** as a draft. Read it, edit the
terms if you want (expiry, budget ceiling, the reserved list), then sign.

> **OWNER-ONLY CEREMONY.** Agents may print the commands below, but must never run
> card-status, key-generation/export, detached-signing, or equivalent key-material
> commands on the owner's behalf. A failed attempt is not permission to retry.

---

## Recommended: hardware token (GPG mode)

v1 verifies **GPG** signatures only (the SSH `-Y` path is deferred, spec §10), so the
token must be in OpenPGP/GPG mode. `gpg 2.4.9` is installed on this box; YubiKey 5
(and most FIDO2+OpenPGP tokens) support this.

```bash
# 0. Insert the token. Confirm GPG applet + your key are on it:
gpg --card-status

# 1. If you have no OpenPGP key on the token yet, generate one (or transfer an
#    existing subkey). The UID should carry your approval principal:
#      JonasAbde <147070826+JonasAbde@users.noreply.github.com>
#    (gpg --full-gen-key, then move the SECRET KEY to the token with
#     --expert --edit-key ... key>  ;  or use yubico-piv-tool / scdaemon.)

# 2. Export the PUBLIC key into the repo (private key stays on the token):
gpg --armor --export <YOUR_FINGERPRINT> > keys/owner.pub.asc

# 3. Review + finalize the mandate terms in keys/delegation_record.json.

# 4. Sign the record. This TOUCHES THE TOKEN — the one act the agent cannot do:
gpg --detach-sign --armor -u <YOUR_FINGERPRINT> \
    --output keys/delegation_record.sig \
    keys/delegation_record.json

# 5. Verify it yourself before committing:
gpg --verify keys/delegation_record.sig keys/delegation_record.json

# 6. Commit the three files. Nothing secret is in them:
git add keys/delegation_record.json keys/delegation_record.sig keys/owner.pub.asc
git commit -m "feat(authority): root the owner-authority proxy (owner-signed mandate)"
git push origin feat/jar-exp-0015-execution-path-live
```

After step 6 the spine is rooted. The agent (the `owner-authority` face) can then run
`sign_calibration_gate` and Gate B closes with truthful provenance — `approved_by`
naming your authority, `signed_by_hand` naming the agent's hand, `delegation_ref`
naming this record.

---

### Windows troubleshooting: `OpenPGP card not available: Service is not running`

On Windows/Gpg4win, do **not** translate that message into a Linux `pcscd` diagnosis.
The relevant OS service is Windows Smart Card (`SCardSvr`) plus GnuPG's `scdaemon`.
The owner can inspect/restart them from an owner-controlled shell (administrator rights
may be required to start the Windows service):

```powershell
Get-Service SCardSvr
Start-Service SCardSvr
gpgconf --kill scdaemon
gpgconf --launch scdaemon
gpg --card-status
```

If the token is still unavailable, sign on another owner-controlled machine and copy
only `owner.pub.asc` and `delegation_record.sig` back. Never copy the private key.

---

## Weaker alternative: same-machine GPG key (documented, not recommended)

If you have no token right now, you can sign with a software key generated on this
box. **Name the flaw plainly:** the secret keyring under `~/.gnupg/private-keys-v1.d/`
is readable by any process running as your user — including the agent — and
`gpg-agent` caches the passphrase. So this root is *verifiable but not
unforgeable*: it stops accidental or careless bypass, not a determined in-band
actor. It is a root-of-trust-shaped decoration until you rotate to a token.

If you choose it anyway, set `"custody": "same-machine-gpg"` in
`keys/delegation_record.json` **before** signing, so the approval record's
`authority_basis` says so truthfully (the spine copies that field into provenance).
Then:

```bash
gpg --full-generate-key          # ed25519, passphrase-protected
gpg --armor --export <FPR> > keys/owner.pub.asc
gpg --detach-sign --armor -u <FPR> --output keys/delegation_record.sig keys/delegation_record.json
gpg --verify keys/delegation_record.sig keys/delegation_record.json
```

Rotate to a hardware token as soon as one is available: re-sign the record with the
token key, re-export `owner.pub.asc`, and commit. The old `delegation_ref` should be
poisoned by a revocation (below).

---

## Revoking the mandate

A revocation is itself an owner-signed record the spine polls live. To revoke:

```bash
# keys/revocation_<YYYYMMDD>.json  (see authority/owner_proxy/revocation.py schema):
#   {"schema_version":"aftergraph.owner-proxy-revocation/0.1",
#    "revokes_delegation_ref":"<sha256 of the record you are revoking>",
#    "revoked_at":"2026-...+00:00",
#    "reason":"rotated to hardware token / compromised / expired early"}
gpg --detach-sign --armor -u <FPR> --output keys/revocation_<YYYYMMDD>.json.sig keys/revocation_<YYYYMMDD>.json
git add keys/revocation_<YYYYMMDD>.json keys/revocation_<YYYYMMDD>.json.sig
```

`delegation_ref` is the SHA-256 of the canonical record; compute it with:

```bash
python -c "from authority.owner_proxy import delegation_ref; import json,sys; print(delegation_ref(json.load(open('keys/delegation_record.json'))))"
```

From the revocation's `revoked_at` forward, the spine refuses every act under that
`delegation_ref` (`mandate_revoked`). The CI audit rejects new ledger entries that
rely on a poisoned root.

---

## What the spine checks on every signing act

`authority/owner_proxy/sign_gate.py` → `sign_calibration_gate`:

1. `delegation_record.json` parses and is structurally valid.
2. `delegation_record.sig` is a good detached GPG signature **by the single key in
   `owner.pub.asc`** (else `record_tampered` / `signature_key_mismatch` / `pubkey_unknown`).
3. No live revocation poisons this `delegation_ref` at `now`.
4. The mandate is unexpired, in-effect (`not_before`), the action is in `scope`, its
   matter is not in `reserved_matters`, and the gate's real bindings (manifest, model,
   calls, cost) match `experiment_binding` and stay under `budget_ceiling_usd`.
5. Only then does it write the approval record, wire the gate, verify the tree reached
   `READY_TO_CALIBRATE`, and append the ledger (the commit point). Any failure before
   the commit rolls the tree back byte-identically.

Delete this directory's `.sig`/`.asc` and the spine fails closed to
`signature_missing`/`pubkey_unknown` — it never signs on an unverifiable root.