from pathlib import Path
P=Path(__file__).resolve().parents[1]/"STUDY-012-GROUNDED-VERIFICATION-TRACE-PREREGISTRATION.md"
def test_study012_preregistration_contains_r1_r2_gates():
 s=P.read_text(encoding="utf-8")
 for x in ["PREREGISTERED-DRAFT","LLM judge only","deterministic oracle","stale state","revocation","contradiction","isolation","constraint decay","replay","crash/recovery","forged evidence","Zero denominators produce UNKNOWN","MUST NOT independently establish canonical VERIFIED","owner approval"]:
  assert x in s
def test_study012_does_not_retroactively_count_prior_studies():
 s=P.read_text(encoding="utf-8")
 assert "not retroactively counted as STUDY-012 observations" in s
