import jev_engineering as jev


def test_version_is_v215():
    assert jev.__version__ == "2.15.0"


def test_v215_counterfactual_symbols_exported():
    for name in ["CounterfactualRouter","CalibrationLedger","ShadowObservation","CompetenceDecayPolicy","TopologyOutcomeMemory"]:
        assert hasattr(jev,name)


def test_v215_sealed_secret_symbols_exported():
    for name in ["SealedSecretBundle","seal_values","unseal_values","generate_runner_seal_keypair"]:
        assert hasattr(jev,name)