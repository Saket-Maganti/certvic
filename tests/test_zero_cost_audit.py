from certvic.validation.zero_cost import validate_zero_cost_config


def test_zero_cost_catches_paid_enabled(tmp_path):
    config = tmp_path / "bad.yaml"
    config.write_text("paid_services_enabled: true\n", encoding="utf-8")
    assert not validate_zero_cost_config(str(config))["passed"]
