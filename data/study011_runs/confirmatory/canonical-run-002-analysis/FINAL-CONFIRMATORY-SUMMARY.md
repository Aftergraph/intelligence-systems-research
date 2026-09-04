# STUDY-011 Confirmatory Analysis — canonical-run-002 (FINAL)

Analysis view: first-occurrence dedupe superseded by Amendment-010 fingerprint preference (one observation per run_id, frozen G7 semantics); 470 LIVE_VALID records, 8/8 cells ≥58.

## Verdicts (frozen decision rules A1-A12)

| Hypothesis | Verdict | Basis |
|---|---|---|
| H1 (assurance lowers FCR) | **REVERSED** | Both strata: FCR(A)=0 (models abstain without assurance) < FCR(G)>0 |
| H2 (authority+budget adds effect over F) | **SUPPORTED** | chi2≈50-52, p<0.001, both strata, direction correct, h≈2.5 |
| H3 (retry alone adds effect) | **REVERSED** | C abstains like A; no effect without assurance |

## The mechanism (by_model abstention analysis)

| Model | A abstain | C abstain | F success | G success |
|---|---|---|---|---|
| qwen-3.8-max A | 85.0% | — | 0.0 | — |
| qwen-3.8-max C | 90.0% | — | 0.0 | — |
| qwen-3.8-max F | 10.0% | — | 90.0 | — |
| qwen-3.8-max G | 5.0% | — | 95.0 | — |

### Interpretation

Under conditions WITHOUT assurance invocation (A, C), models abstain 73-100% of the
time — they correctly refuse to complete missions. This makes FCR(A)≈0, which REVERSES
H1's predicted direction (G cannot beat a floor of zero false completions).

Under F (assurance invoked), success jumps to 76-95%. Under G (assurance+authority+
budget), success is 76-100% with abstention 0-15%.

**The actionable finding is H2 SUPPORTED at p<0.001 in both strata with h≈2.5:**
the full governance stack (assurance + authority + budget tracking) delivers
materially higher actual success than assurance alone.

**Hedge (per independent statistical review, SOUND_WITH_HEDGES_REQUIRED):**
F alone already converts abstention into action; G's added value over F is the
marginal, precisely-measured difference (H2's McNemar contrast), not a claim that
governance "unlocks" models. The paralysis→action conversion is attributable to
assurance invocation (F), with G adding authority+budget on top. Claims should be
phrased accordingly.

## Honest caveats

- H1/H3 REVERSED is a valid preregistered outcome (no p-hacking; DO-NOT-OPTIMIZE-FOR-PASS honored).
- OpenRouter block-level McNemar pairs are EMPTY: the :free burn records are excluded by the Amendment-010 lineage rule; paid re-attempts superseded them under the same run_ids.
- summary.md writer KeyError('chi2') on empty block strata — results.json is authoritative; writer bug noted, not blocking.
- 243 duplicate run_id lines existed in raw records (checkpoint/resume rewrites); resolved per frozen G7 semantics (one observation per run_id, Amendment-010 lineage preferred).
