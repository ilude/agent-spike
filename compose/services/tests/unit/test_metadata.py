"""Test metadata flattening."""

import json
from compose.services.metadata.flattener import flatten_video_metadata, _make_safe_key


def test_flatten_simple_fields():
    """Test flattening simple pass-through fields."""
    tags = {
        "content_style": "tutorial",
        "difficulty": "intermediate"
    }

    result = flatten_video_metadata(tags)

    assert result["content_style"] == "tutorial"
    assert result["difficulty"] == "intermediate"
    assert "tags_json" in result


def test_flatten_subject_matter():
    """Test flattening subject_matter list."""
    tags = {
        "subject_matter": ["AI Agents", "Python", "Multi-Agent Systems"]
    }

    result = flatten_video_metadata(tags)

    assert result["subject_ai_agents"] is True
    assert result["subject_python"] is True
    assert result["subject_multi_agent_systems"] is True


def test_flatten_entities_people():
    """Test flattening people entities."""
    tags = {
        "entities": {
            "people": ["Sam Altman", "Demis Hassabis"]
        }
    }

    result = flatten_video_metadata(tags)

    assert result["person_sam_altman"] is True
    assert result["person_demis_hassabis"] is True


def test_flatten_entities_companies():
    """Test flattening company entities."""
    tags = {
        "entities": {
            "companies": ["Anthropic", "OpenAI", "DeepMind"]
        }
    }

    result = flatten_video_metadata(tags)

    assert result["company_anthropic"] is True
    assert result["company_openai"] is True
    assert result["company_deepmind"] is True


def test_flatten_entities_named_things():
    """Test flattening named_things entities."""
    tags = {
        "entities": {
            "named_things": ["Claude", "GPT-4", "LangChain"]
        }
    }

    result = flatten_video_metadata(tags)

    assert result["named_thing_claude"] is True
    assert result["named_thing_gpt_4"] is True
    assert result["named_thing_langchain"] is True


def test_flatten_references():
    """Test flattening references."""
    tags = {
        "references": [
            {"name": "MCP", "type": "protocol"},
            {"name": "Claude API", "type": "documentation"},
            {"name": "Research Paper", "type": "paper"}
        ]
    }

    result = flatten_video_metadata(tags)

    assert result["ref_mcp"] is True
    assert result["ref_claude_api"] is True
    assert result["ref_research_paper"] is True
    assert result["ref_type_protocol"] is True
    assert result["ref_type_documentation"] is True
    assert result["ref_type_paper"] is True


def test_flatten_complete_structure():
    """Test flattening complete structured metadata."""
    tags = {
        "subject_matter": ["AI Agents", "Python"],
        "entities": {
            "people": ["Sam Altman"],
            "companies": ["Anthropic", "OpenAI"],
            "named_things": ["Claude", "GPT-4"]
        },
        "references": [
            {"name": "MCP", "type": "protocol"}
        ],
        "content_style": "tutorial",
        "difficulty": "advanced"
    }

    result = flatten_video_metadata(tags)

    # Check all categories present
    assert result["subject_ai_agents"] is True
    assert result["subject_python"] is True
    assert result["person_sam_altman"] is True
    assert result["company_anthropic"] is True
    assert result["company_openai"] is True
    assert result["named_thing_claude"] is True
    assert result["named_thing_gpt_4"] is True
    assert result["ref_mcp"] is True
    assert result["ref_type_protocol"] is True
    assert result["content_style"] == "tutorial"
    assert result["difficulty"] == "advanced"

    # Verify JSON backup
    assert "tags_json" in result
    restored = json.loads(result["tags_json"])
    assert restored == tags


def test_flatten_empty():
    """Test flattening empty metadata."""
    tags = {}

    result = flatten_video_metadata(tags)

    # Should only have tags_json
    assert "tags_json" in result
    assert len(result) == 1


def test_make_safe_key():
    """Test _make_safe_key helper function."""
    assert _make_safe_key("subject", "AI Agents") == "subject_ai_agents"
    assert _make_safe_key("person", "Sam Altman") == "person_sam_altman"
    assert _make_safe_key("company", "Anthropic-AI") == "company_anthropic_ai"
    assert _make_safe_key("named_thing", "GPT-4") == "named_thing_gpt_4"
    assert _make_safe_key("ref", "Multi-Agent Systems") == "ref_multi_agent_systems"


def test_flatten_missing_optional_fields():
    """Test that missing optional fields don't cause errors."""
    tags = {
        "subject_matter": ["AI"]
        # Missing entities, references, content_style, difficulty
    }

    result = flatten_video_metadata(tags)

    assert result["subject_ai"] is True
    assert "tags_json" in result
    # No errors for missing fields
