"""Parity: same DSL line → same result shape (offline verbs)."""

from dsl2koru import dispatch


def test_parity_text_vs_dict() -> None:
    line = "VALIDATE_LANE IDE auto INSTANCE default"
    r1 = dispatch(line)
    r2 = dispatch({"verb": "VALIDATE_LANE", "ide": "auto", "instance": "default"})
    assert r1.ok == r2.ok
    assert r1.verb == r2.verb == "VALIDATE_LANE"


def test_parity_text_vs_protobuf() -> None:
    from dsl2koru.codec import envelope_to_bytes

    line = "VALIDATE_LANE IDE auto INSTANCE default"
    r1 = dispatch(line)
    pb = envelope_to_bytes({"verb": "VALIDATE_LANE", "ide": "auto", "instance": "default"})
    r2 = dispatch(pb)
    assert r1.ok == r2.ok
    assert r1.verb == r2.verb
