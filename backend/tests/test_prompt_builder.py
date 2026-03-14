"""Tests for prompt construction logic."""

from __future__ import annotations

from app.prompt_builder import build_messages, build_system_prompt
from app.schemas import ChatMessage

SAMPLE_PROFILE = {
    "center": {"lat": 52.52, "lon": 13.405},
    "radius_m": 800,
    "counts": {"amenity": {"cafe": 5, "restaurant": 12}},
    "nearest": {"amenity/cafe": {"name": "Corner Café", "distance_m": 45.2}},
    "mobility": {"bus_stop": 7},
    "land_use": {"residential": 3},
    "poi_examples": {"cafe": ["Corner Café", "Bean House"]},
    "data_quality_notes": [],
}


class TestBuildSystemPrompt:
    def test_contains_grounding_policy(self):
        prompt = build_system_prompt(SAMPLE_PROFILE)
        assert "Grounding Policy" in prompt
        assert "Do not fabricate" in prompt

    def test_contains_region_data(self):
        prompt = build_system_prompt(SAMPLE_PROFILE)
        assert '"center"' in prompt
        assert "52.52" in prompt
        assert "13.405" in prompt
        assert "Corner Café" in prompt

    def test_contains_response_format_instructions(self):
        prompt = build_system_prompt(SAMPLE_PROFILE)
        assert '"answer"' in prompt
        assert '"evidence"' in prompt
        assert '"confidence"' in prompt
        assert "JSON object" in prompt

    def test_contains_mobility_data(self):
        prompt = build_system_prompt(SAMPLE_PROFILE)
        assert '"bus_stop": 7' in prompt

    def test_contains_counts(self):
        prompt = build_system_prompt(SAMPLE_PROFILE)
        assert '"cafe": 5' in prompt
        assert '"restaurant": 12' in prompt


class TestBuildMessages:
    def test_prepends_system_message(self):
        msgs = build_messages(
            [ChatMessage(role="user", content="Is this walkable?")],
            SAMPLE_PROFILE,
        )
        assert len(msgs) == 2
        assert msgs[0]["role"] == "system"
        assert "Grounding Policy" in msgs[0]["content"]

    def test_preserves_chat_history_order(self):
        history = [
            ChatMessage(role="user", content="How walkable?"),
            ChatMessage(role="assistant", content="Quite walkable."),
            ChatMessage(role="user", content="What about transit?"),
        ]
        msgs = build_messages(history, SAMPLE_PROFILE)
        assert len(msgs) == 4
        assert msgs[1] == {"role": "user", "content": "How walkable?"}
        assert msgs[2] == {"role": "assistant", "content": "Quite walkable."}
        assert msgs[3] == {"role": "user", "content": "What about transit?"}

    def test_single_user_message(self):
        msgs = build_messages(
            [ChatMessage(role="user", content="Tell me about this area")],
            SAMPLE_PROFILE,
        )
        assert len(msgs) == 2
        assert msgs[1]["role"] == "user"
        assert msgs[1]["content"] == "Tell me about this area"

    def test_system_prompt_contains_region_data(self):
        msgs = build_messages(
            [ChatMessage(role="user", content="test")],
            SAMPLE_PROFILE,
        )
        system_content = msgs[0]["content"]
        assert "52.52" in system_content
        assert "Corner Café" in system_content

    def test_empty_profile_still_produces_valid_prompt(self):
        empty_profile = {
            "center": {"lat": 0.0, "lon": 0.0},
            "radius_m": 100,
            "counts": {},
            "nearest": {},
            "mobility": {},
            "land_use": {},
            "poi_examples": {},
            "data_quality_notes": [],
        }
        msgs = build_messages(
            [ChatMessage(role="user", content="Anything here?")],
            empty_profile,
        )
        assert len(msgs) == 2
        assert "Grounding Policy" in msgs[0]["content"]
