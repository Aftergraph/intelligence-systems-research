import json
import httpx
from jev_engineering.provider_health import check_typesafe, check_dialagram, run_provider_smoke

def ts_handler(req):
    if req.url.path.endswith('/v1/models'):
        return httpx.Response(200,json={'data':[{'id':'jev-latest'}]},headers={'x-request-id':'ts-models'})
    return httpx.Response(200,json={'model':'jev-latest','answers':{'continue':{'noul':.9}},'usage':{}},headers={'x-request-id':'ts-system'})

def dg_handler(req):
    if req.url.path.endswith('/models'):
        return httpx.Response(200,json={'data':[{'id':'q'}]},headers={'x-request-id':'dg-models'})
    return httpx.Response(200,json={'id':'dg-payload','model':'q','choices':[{'message':{'content':'OK'}}]},headers={'x-trace-id':'dg-trace'})

def test_typesafe_systemone_captures_request_id():
    rows=check_typesafe(api_key='dummy',transport=httpx.MockTransport(ts_handler)); assert rows[-1].request_ids==('ts-system',)
def test_dialagram_chat_captures_header_and_payload_id():
    rows=check_dialagram(api_key='dummy',transport=httpx.MockTransport(dg_handler)); assert rows[-1].request_ids==('dg-trace','dg-payload')
def test_provider_check_serializes_request_ids():
    row=check_typesafe(api_key='dummy',transport=httpx.MockTransport(ts_handler))[-1].to_dict(); assert row['request_ids']==['ts-system']
def test_run_provider_smoke_reports_lineage(monkeypatch):
    from jev_engineering import provider_health as ph
    monkeypatch.setattr(ph,'check_typesafe',lambda **kw:[ph.ProviderCheck('typesafe','system_one',True,1,'ok',('a',))])
    monkeypatch.setattr(ph,'check_dialagram',lambda **kw:[ph.ProviderCheck('dialagram','chat_completions',True,1,'ok',('b',))])
    r=ph.run_provider_smoke(typesafe_api_key='x',dialagram_api_key='y'); assert r['request_lineage_present'] is True and r['authenticated_https'] is True