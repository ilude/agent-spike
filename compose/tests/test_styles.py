"""Tests for the writing styles service."""

import pytest

from compose.services.styles import (
    PRESET_STYLES,
    StyleId,
    StylesService,
    WritingStyle,
    get_styles_service,
)


class TestWritingStyle:
    """Tests for WritingStyle model."""

    def test_style_model_creation(self):
        """Test creating a WritingStyle instance."""
        style = WritingStyle(
            id=StyleId.DEFAULT,
            name="Test",
            description="Test description",
            system_prompt_modifier="Test modifier",
        )
        assert style.id == StyleId.DEFAULT
        assert style.name == "Test"
        assert style.description == "Test description"
        assert style.system_prompt_modifier == "Test modifier"
        assert style.icon == ""

    def test_style_model_with_icon(self):
        """Test creating a style with icon."""
        style = WritingStyle(
            id=StyleId.CONCISE,
            name="Short",
            description="Brief",
            system_prompt_modifier="Be brief",
            icon="bolt",
        )
        assert style.icon == "bolt"


class TestPresetStyles:
    """Tests for preset style definitions."""

    def test_all_style_ids_have_presets(self):
        """Test that all StyleId enum values have preset definitions."""
        for style_id in StyleId:
            assert style_id in PRESET_STYLES, f"Missing preset for {style_id}"

    def test_default_style_has_no_modifier(self):
        """Test that default style has empty modifier."""
        default = PRESET_STYLES[StyleId.DEFAULT]
        assert default.system_prompt_modifier == ""

    def test_non_default_styles_have_modifiers(self):
        """Test that non-default styles have modifiers."""
        for style_id, style in PRESET_STYLES.items():
            if style_id != StyleId.DEFAULT:
                assert (
                    style.system_prompt_modifier != ""
                ), f"{style_id} should have a modifier"

    def test_concise_style_content(self):
        """Test concise style has appropriate content."""
        concise = PRESET_STYLES[StyleId.CONCISE]
        assert "concise" in concise.system_prompt_modifier.lower()
        assert concise.name == "Concise"

    def test_detailed_style_content(self):
        """Test detailed style has appropriate content."""
        detailed = PRESET_STYLES[StyleId.DETAILED]
        assert "detailed" in detailed.system_prompt_modifier.lower()
        assert detailed.name == "Detailed"


class TestStylesService:
    """Tests for StylesService class."""

    @pytest.fixture
    def service(self):
        """Create a fresh service instance for testing."""
        return StylesService()

    def test_list_styles_returns_all(self, service):
        """Test list_styles returns all preset styles."""
        styles = service.list_styles()
        assert len(styles) == len(StyleId)
        assert all(isinstance(s, WritingStyle) for s in styles)

    def test_list_styles_includes_all_ids(self, service):
        """Test list_styles includes all style IDs."""
        styles = service.list_styles()
        style_ids = {s.id for s in styles}
        assert style_ids == set(StyleId)

    def test_get_style_by_string(self, service):
        """Test getting style by string ID."""
        style = service.get_style("concise")
        assert style is not None
        assert style.id == StyleId.CONCISE

    def test_get_style_by_enum(self, service):
        """Test getting style by enum value (as string)."""
        style = service.get_style(StyleId.FORMAL.value)
        assert style is not None
        assert style.id == StyleId.FORMAL

    def test_get_style_invalid_id(self, service):
        """Test getting style with invalid ID returns None."""
        style = service.get_style("nonexistent")
        assert style is None

    def test_get_style_empty_id(self, service):
        """Test getting style with empty ID returns None."""
        style = service.get_style("")
        assert style is None

    def test_get_system_prompt_modifier_valid(self, service):
        """Test getting modifier for valid style."""
        modifier = service.get_system_prompt_modifier("technical")
        assert "technical" in modifier.lower()

    def test_get_system_prompt_modifier_default(self, service):
        """Test getting modifier for default style returns empty."""
        modifier = service.get_system_prompt_modifier("default")
        assert modifier == ""

    def test_get_system_prompt_modifier_invalid(self, service):
        """Test getting modifier for invalid style returns empty."""
        modifier = service.get_system_prompt_modifier("invalid")
        assert modifier == ""

    def test_apply_style_to_prompt_with_modifier(self, service):
        """Test applying style modifier to base prompt."""
        base = "You are a helpful assistant."
        result = service.apply_style_to_prompt(base, "concise")
        assert "STYLE INSTRUCTION:" in result
        assert base in result
        # Style should come first
        assert result.index("STYLE") < result.index("helpful")

    def test_apply_style_to_prompt_default(self, service):
        """Test applying default style doesn't modify prompt."""
        base = "You are a helpful assistant."
        result = service.apply_style_to_prompt(base, "default")
        assert result == base

    def test_apply_style_to_prompt_invalid(self, service):
        """Test applying invalid style doesn't modify prompt."""
        base = "You are a helpful assistant."
        result = service.apply_style_to_prompt(base, "invalid")
        assert result == base

    def test_apply_style_custom_separator(self, service):
        """Test applying style with custom separator."""
        base = "Base prompt"
        result = service.apply_style_to_prompt(base, "concise", separator="\n---\n")
        assert "\n---\n" in result


class TestStylesSingleton:
    """Tests for singleton pattern."""

    def test_get_styles_service_returns_service(self):
        """Test get_styles_service returns StylesService instance."""
        service = get_styles_service()
        assert isinstance(service, StylesService)

    def test_get_styles_service_returns_same_instance(self):
        """Test get_styles_service returns same instance."""
        service1 = get_styles_service()
        service2 = get_styles_service()
        assert service1 is service2


class TestStyleIdEnum:
    """Tests for StyleId enum."""

    def test_all_style_ids_are_strings(self):
        """Test all StyleId values are lowercase strings."""
        for style_id in StyleId:
            assert style_id.value == style_id.value.lower()

    def test_style_id_from_string(self):
        """Test converting string to StyleId."""
        assert StyleId("concise") == StyleId.CONCISE
        assert StyleId("default") == StyleId.DEFAULT

    def test_style_id_invalid_string(self):
        """Test invalid string raises ValueError."""
        with pytest.raises(ValueError):
            StyleId("invalid")
