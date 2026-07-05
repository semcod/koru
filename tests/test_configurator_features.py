from __future__ import annotations

from koru.configurator.features import (
    _TOGGLEABLE_FEATURES,
    default_v2_feature_sections,
    merge_v2_feature_sections,
)


def test_default_v2_feature_sections_has_all_sections_disabled() -> None:
    defaults = default_v2_feature_sections()
    assert set(defaults) == {"vision", "mesh", "browse", "delegate", "sandbox"}
    # toggleable feature sections are disabled by default
    for name in _TOGGLEABLE_FEATURES:
        assert defaults[name]["enabled"] is False
    # a couple of representative inner defaults
    assert defaults["vision"]["interval_seconds"] == 30
    assert defaults["mesh"]["discovery"] == "mdns"
    assert defaults["delegate"]["accept"] == []


def test_default_v2_feature_sections_is_a_fresh_copy_each_call() -> None:
    first = default_v2_feature_sections()
    first["vision"]["enabled"] = True
    first["extra"] = "mutated"
    second = default_v2_feature_sections()
    assert second["vision"]["enabled"] is False
    assert "extra" not in second


def test_merge_fills_missing_sections() -> None:
    merged = merge_v2_feature_sections({})
    assert set(merged) >= {"vision", "mesh", "browse", "delegate", "sandbox"}
    assert merged["vision"]["enabled"] is False


def test_merge_keeps_existing_enabled_and_fills_nested_defaults() -> None:
    config = {"vision": {"enabled": True}}
    merged = merge_v2_feature_sections(config)
    assert merged["vision"]["enabled"] is True  # not overwritten
    assert merged["vision"]["interval_seconds"] == 30  # default filled in
    assert merged["vision"]["format"] == "webp"


def test_merge_overrides_defaults_with_user_values() -> None:
    config = {"vision": {"interval_seconds": 120, "format": "png"}}
    merged = merge_v2_feature_sections(config)
    assert merged["vision"]["interval_seconds"] == 120
    assert merged["vision"]["format"] == "png"
    # untouched defaults still present
    assert merged["vision"]["enabled"] is False
    assert merged["vision"]["monitors"] == "all"


def test_merge_replaces_non_dict_section_with_defaults() -> None:
    config = {"vision": "broken", "mesh": 123}
    merged = merge_v2_feature_sections(config)
    assert merged["vision"] == default_v2_feature_sections()["vision"]
    assert merged["mesh"] == default_v2_feature_sections()["mesh"]


def test_merge_does_not_mutate_input() -> None:
    config = {"vision": {"enabled": True}}
    merge_v2_feature_sections(config)
    assert config == {"vision": {"enabled": True}}  # untouched
    assert "interval_seconds" not in config["vision"]


def test_merge_preserves_unrelated_top_level_keys() -> None:
    config = {"schema": "koru.config/v1", "ide": "windsurf", "serve": {"port": 9000}}
    merged = merge_v2_feature_sections(config)
    assert merged["schema"] == "koru.config/v1"
    assert merged["ide"] == "windsurf"
    assert merged["serve"] == {"port": 9000}
