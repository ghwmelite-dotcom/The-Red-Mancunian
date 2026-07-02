import pytest
from engine import simulate
from schema import validate, SchemaError


def test_simulate_output_validates():
    m = simulate("MUN", "RMA", competition="ucl", seed=13)
    assert validate(m) is m


def test_missing_key_raises():
    m = simulate("MUN", "RMA", seed=13)
    del m["winprob"]
    with pytest.raises(SchemaError):
        validate(m)


def test_bad_event_type_raises():
    m = simulate("MUN", "RMA", seed=13)
    m["events"][0]["type"] = "bogus"
    with pytest.raises(SchemaError):
        validate(m)


def test_bad_scoreafter_format_raises():
    m = simulate("MUN", "RMA", seed=13)
    ft = [e for e in m["events"] if e["type"] == "full_time"][0]
    ft["scoreAfter"] = "2:1"
    with pytest.raises(SchemaError):
        validate(m)
