from scripts.study012_postrun_v4 import analyze,validate_analysis,wilson

def test_postrun_v4_canonical_analysis():
    a=analyze()
    validate_analysis(a)
    assert a["hypothesis_dispositions"]["H1"]["status"]=="SUPPORTED"
    assert a["hypothesis_dispositions"]["H2"]["status"]=="WALKED_BACK"
    assert a["hypothesis_dispositions"]["H3"]["status"]=="SUPPORTED"
    assert a["hypothesis_dispositions"]["H4"]["status"]=="SUPPORTED"
    assert a["condition_summary"]["J"]["canonical"]=={"UNESTABLISHED":240}
    assert a["condition_summary"]["D"]["canonical"]=={"VERIFIED":240}
    assert a["condition_summary"]["JD"]["canonical"]=={"VERIFIED":240}
    assert a["condition_summary"]["DI"]["canonical"]=={"VERIFIED":240}

def test_zero_of_240_wilson_bound_is_nonzero_upper():
    lo,hi=wilson(0,240)
    assert lo==0.0
    assert 0.015 < hi < 0.016
