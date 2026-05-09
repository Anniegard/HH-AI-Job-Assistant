"""Tests for app/config/search_profiles.py (Stage 4)."""

from __future__ import annotations

import pytest

from app.config.search_profiles import (
    DEFAULT_PROFILE_NAME,
    PROFILES,
    get_profile,
    list_profiles,
)

EXPECTED_PROFILE_KEYS = {
    "ai_builder",
    "python_automation",
    "ai_automation",
    "fastapi_backend",
    "llm_engineer",
    "ai_product_engineer",
}


def test_profiles_dict_has_all_expected_keys():
    assert set(PROFILES.keys()) == EXPECTED_PROFILE_KEYS


def test_profiles_dict_is_non_empty():
    assert len(PROFILES) == 6


def test_each_profile_name_matches_dict_key():
    for key, profile in PROFILES.items():
        assert profile.name == key, f"Profile name mismatch for key '{key}'"


def test_each_profile_has_non_empty_display_name():
    for profile in PROFILES.values():
        assert profile.display_name, f"Empty display_name for profile '{profile.name}'"


def test_each_profile_has_non_empty_query():
    for profile in PROFILES.values():
        assert profile.query, f"Empty query for profile '{profile.name}'"


def test_each_profile_area_is_positive():
    for profile in PROFILES.values():
        assert profile.area > 0, f"Invalid area for profile '{profile.name}'"


def test_get_profile_returns_correct_profile():
    profile = get_profile("ai_builder")
    assert profile is not None
    assert profile.name == "ai_builder"
    assert profile.display_name == "AI Builder"


def test_get_profile_returns_none_for_unknown():
    assert get_profile("nonexistent_profile") is None
    assert get_profile("") is None


def test_list_profiles_returns_all():
    profiles = list_profiles()
    assert len(profiles) == len(PROFILES)
    names = {p.name for p in profiles}
    assert names == EXPECTED_PROFILE_KEYS


def test_default_profile_name_in_profiles():
    assert DEFAULT_PROFILE_NAME in PROFILES


def test_default_profile_is_ai_builder():
    assert DEFAULT_PROFILE_NAME == "ai_builder"


def test_profile_keywords_boost_is_tuple():
    for profile in PROFILES.values():
        assert isinstance(profile.keywords_boost, tuple), (
            f"keywords_boost must be tuple for '{profile.name}'"
        )


def test_profile_penalties_is_tuple():
    for profile in PROFILES.values():
        assert isinstance(profile.penalties, tuple), (
            f"penalties must be tuple for '{profile.name}'"
        )


def test_search_profile_is_frozen():
    profile = get_profile("ai_builder")
    with pytest.raises((AttributeError, TypeError)):
        profile.name = "modified"  # type: ignore[misc]


def test_fastapi_profile_query_contains_fastapi():
    profile = get_profile("fastapi_backend")
    assert "FastAPI" in profile.query or "fastapi" in profile.query.lower()


def test_llm_engineer_profile_query_contains_llm():
    profile = get_profile("llm_engineer")
    query_lower = profile.query.lower()
    assert "llm" in query_lower or "openai" in query_lower or "gpt" in query_lower


def test_all_profiles_have_russia_as_default_area():
    for profile in PROFILES.values():
        assert profile.area == 113, (
            f"Expected area=113 (Russia) for '{profile.name}', got {profile.area}"
        )
