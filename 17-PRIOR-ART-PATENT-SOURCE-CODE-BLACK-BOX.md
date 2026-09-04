# Prior Art, Patent, Source Code and Black-Box Research

## Principle
Prior art must be searched in more than academic literature.

## Five reconnaissance tracks
1. Papers / scholarly work
2. Patents
3. Standards / RFCs / specifications
4. Source code / issues / PRs / release history
5. Products / black-box behavioral testing

## Patent workflow
Concept
→ synonyms
→ CPC/IPC classifications
→ patent database search
→ families
→ cited and forward prior art
→ claims
→ file/prosecution history where relevant
→ novelty map.

Read claims, not just abstracts.

## Source-code archaeology
Search:
frameworks, SDKs, schemas, test suites, examples, issues, PRs, commits and release history.

A research statement like:
“frameworks do not implement X”
requires code-level reconnaissance.

## Black-box research
For closed systems, test observable behavior through authorized/public interfaces.

Candidate families:
- objective retention
- constraint retention
- state changes
- revocation
- delegation
- recovery
- completion behavior
- verification behavior
- cost behavior
- context loss
- persistence/memory
- portability
- human interruption
- security/adversarial robustness

## Differential testing
Run the same mission against multiple systems and compare:
verified success, false completion, cost, latency, actions, retries, constraints, recovery and evidence.

## Search-date integrity
Freeze corpus by date when making historical novelty statements.

## Negative search log
A “no prior art found” claim is invalid without recording:
databases, queries, synonyms, classifications, date, filters, inspected results, languages and limitations.

Preferred wording:
“No materially equivalent implementation was identified within the documented search scope.”

## IP gate
Discovery → private invention record → prior-art search → technical-effect analysis → patent decision → filing/public release → publication.

Do not publicly disclose potentially patent-sensitive mechanisms before an informed filing decision.
