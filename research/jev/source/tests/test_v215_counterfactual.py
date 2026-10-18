from __future__ import annotations
import hashlib
import pytest
from jev_engineering.adaptive_swarm import AdaptiveCompetenceRouter, CompetenceLedger, VerifiedOutcome
from jev_engineering.counterfactual_routing import *
from jev_engineering.heterogeneous_agents import BackendBinding, BackendIdentity, BackendKind, BackendRegistry, TopologyMode
from jev_engineering.multi_agent import SubagentSpec


def digest(s): return hashlib.sha256(s.encode()).hexdigest()

def setup_router(a=.9,b=.7):
    reg=BackendRegistry()
    reg.register(BackendIdentity('a',BackendKind.LOCAL,'local','a',capabilities=frozenset({'code'}),competence={'code':a}),lambda *x: {})
    reg.register(BackendIdentity('b',BackendKind.WORKER,'worker','b',capabilities=frozenset({'code'}),competence={'code':b}),lambda *x: {})
    led=CompetenceLedger(alpha=1.0)
    router=AdaptiveCompetenceRouter(reg,(BackendBinding('builder',('a','b'),frozenset({'code'}),'code',0.0),),led)
    return reg,led,router

def test_counterfactual_selected_and_alternate():
    reg,_,router=setup_router(); selected,alts=CounterfactualRouter(router,reg).estimate(SubagentSpec('builder','build'))
    assert selected.backend_id=='a' and alts[0].alternate_backend_id=='b'
def test_counterfactual_modeled_only():
    reg,_,router=setup_router(); _,alts=CounterfactualRouter(router,reg).estimate(SubagentSpec('builder','build')); assert alts[0].modeled_only is True
def test_counterfactual_prediction_matches_ledger():
    reg,_,router=setup_router(); _,alts=CounterfactualRouter(router,reg).estimate(SubagentSpec('builder','build')); assert alts[0].predicted_success==pytest.approx(.7)
def test_counterfactual_id_stable():
    reg,_,router=setup_router(); c=CounterfactualRouter(router,reg); assert c.estimate(SubagentSpec('builder','build'))[1][0].estimate_id==c.estimate(SubagentSpec('builder','build'))[1][0].estimate_id
def test_calibration_requires_matching_backend():
    reg,_,router=setup_router(); est=CounterfactualRouter(router,reg).estimate(SubagentSpec('builder','build'))[1][0]; l=CalibrationLedger(); l.register(est)
    with pytest.raises(ValueError): l.resolve(est.estimate_id,VerifiedOutcome('a','code',True,.9,('v1','v2'),digest('x')))
def test_calibration_brier():
    reg,_,router=setup_router(); est=CounterfactualRouter(router,reg).estimate(SubagentSpec('builder','build'))[1][0]; l=CalibrationLedger(); l.register(est)
    r=l.resolve(est.estimate_id,VerifiedOutcome('b','code',True,1.0,('v1','v2'),digest('x'))); assert r.brier_score==pytest.approx(.09)
def test_calibration_cannot_resolve_twice():
    reg,_,router=setup_router(); est=CounterfactualRouter(router,reg).estimate(SubagentSpec('builder','build'))[1][0]; l=CalibrationLedger(); l.register(est); o=VerifiedOutcome('b','code',True,1.0,('v1','v2'),digest('x')); l.resolve(est.estimate_id,o)
    with pytest.raises(ValueError): l.resolve(est.estimate_id,o)
def test_shadow_modeled_not_learning():
    x=ShadowObservation('t','a','b',False,False,None); assert not x.eligible_for_learning
def test_shadow_measured_unverified_not_learning():
    x=ShadowObservation('t','a','b',True,False,digest('x')); assert not x.eligible_for_learning
def test_shadow_measured_verified_learning():
    x=ShadowObservation('t','a','b',True,True,digest('x')); assert x.eligible_for_learning
def test_decay_zero_epochs_identity(): assert CompetenceDecayPolicy().apply(.8,0).decayed_score==pytest.approx(.8)
def test_decay_moves_toward_prior():
    p=CompetenceDecayPolicy(prior=.5,retention_per_epoch=.5); assert p.apply(.9,2).decayed_score==pytest.approx(.6)
def test_decay_rejects_negative_epoch():
    with pytest.raises(ValueError): CompetenceDecayPolicy().apply(.5,-1)
def test_topology_memory_requires_two_verifiers():
    with pytest.raises(ValueError): TopologyOutcome('code',TopologyMode.PARALLEL,True,1.0,('v1',),digest('x'))
def test_topology_memory_duplicate_evidence_fails():
    m=TopologyOutcomeMemory(); r=TopologyOutcome('code',TopologyMode.PARALLEL,True,1.0,('v1','v2'),digest('x')); m.record(r)
    with pytest.raises(ValueError): m.record(r)
def test_topology_memory_prefers_verified_score():
    m=TopologyOutcomeMemory(); m.record(TopologyOutcome('code',TopologyMode.HIERARCHICAL,True,.6,('v1','v2'),digest('a'))); m.record(TopologyOutcome('code',TopologyMode.PARALLEL,True,.9,('v1','v2'),digest('b'))); assert m.preferred('code') is TopologyMode.PARALLEL
def test_topology_memory_fallback_without_evidence(): assert TopologyOutcomeMemory().preferred('x') is TopologyMode.HIERARCHICAL