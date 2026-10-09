import base64, json
import pytest
from jev_engineering.sealed_secrets import *

def keys():
    private,public=generate_runner_seal_keypair(); return private,base64.b64encode(public).decode()
def test_roundtrip_two_allowlisted_secrets():
    priv,pub=keys(); vals={'TYPESAFE_API_KEY':'dummy-type','DIALAGRAM_API_KEY':'dummy-dial'}; assert unseal_values(seal_values(vals,pub),priv)==vals
def test_ciphertext_does_not_contain_plaintext():
    priv,pub=keys(); b=seal_values({'TYPESAFE_API_KEY':'super-secret-value'},pub); assert 'super-secret-value' not in json.dumps(b.to_dict())
def test_bundle_rejects_unknown_secret():
    _,pub=keys();
    with pytest.raises(ValueError): seal_values({'EVIL':'x'},pub)
def test_bundle_rejects_empty_secret():
    _,pub=keys();
    with pytest.raises(ValueError): seal_values({'TYPESAFE_API_KEY':''},pub)
def test_wrong_private_key_fails():
    _,pub=keys(); priv2,_=generate_runner_seal_keypair(); b=seal_values({'TYPESAFE_API_KEY':'x'},pub)
    with pytest.raises(ValueError): unseal_values(b,priv2)
def test_tampered_ciphertext_fails():
    priv,pub=keys(); b=seal_values({'TYPESAFE_API_KEY':'x'},pub); d=b.to_dict(); c=d['ciphertexts']['TYPESAFE_API_KEY']; d['ciphertexts']['TYPESAFE_API_KEY']=('A' if c[0]!='A' else 'B')+c[1:]
    with pytest.raises(Exception): unseal_values(SealedSecretBundle.from_dict(d),priv)
def test_public_key_rederived_from_private():
    priv,pub=keys(); assert public_key_b64_from_private(priv)==pub
def test_schema_rejects_unknown_version():
    with pytest.raises(ValueError): SealedSecretBundle.from_dict({'schema':'x','key_fingerprint_sha256':'','ciphertexts':{}})
def test_non_allowlisted_in_deserialization_rejected():
    with pytest.raises(ValueError): SealedSecretBundle.from_dict({'schema':'aftergraph.runner-sealed-secrets/1.0','key_fingerprint_sha256':'x','ciphertexts':{'BAD':'x'}})