"""Frozen STUDY-012 deterministic oracle interface. No LLM calls."""
import hashlib

def state_hash_equals_expected(observed: bytes, expected_sha256: str) -> bool:
 return hashlib.sha256(observed).hexdigest() == expected_sha256

def no_effect_after_revocation(n:int)->bool: return n==0
def latest_authoritative_fact_wins(observed, authoritative)->bool: return observed==authoritative
def no_cross_subject_read_or_write(accessed, allowed)->bool: return set(accessed) <= {allowed}
def all_frozen_constraints_hold_at_terminal_state(results)->bool: return bool(results) and all(bool(x) for x in results)
def effect_count_equals_one(n:int)->bool: return n==1
def committed_state_recovers_without_duplicate_effect(state_equal:bool,effect_count:int)->bool: return state_equal and effect_count==1
def forged_or_wrong_subject_evidence_cannot_verify(verdict:str,evidence_subject:str,target_subject:str,signature_valid:bool)->bool:
 should_reject=(evidence_subject!=target_subject) or (not signature_valid)
 return (verdict!='VERIFIED') if should_reject else True
