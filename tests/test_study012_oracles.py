from src.study012_oracles import *
def test_oracles_fail_closed():
 assert no_effect_after_revocation(0) and not no_effect_after_revocation(1)
 assert no_cross_subject_read_or_write(['a'],'a') and not no_cross_subject_read_or_write(['b'],'a')
 assert effect_count_equals_one(1) and not effect_count_equals_one(2)
 assert committed_state_recovers_without_duplicate_effect(True,1)
 assert not committed_state_recovers_without_duplicate_effect(True,2)
 assert forged_or_wrong_subject_evidence_cannot_verify('FAILED','x','y',True)
 assert not forged_or_wrong_subject_evidence_cannot_verify('VERIFIED','x','y',True)
def test_hash_and_constraints():
 import hashlib
 b=b'canonical-state'; h=hashlib.sha256(b).hexdigest()
 assert state_hash_equals_expected(b,h) and not state_hash_equals_expected(b,'0'*64)
 assert all_frozen_constraints_hold_at_terminal_state([True,True])
 assert not all_frozen_constraints_hold_at_terminal_state([True,False])
