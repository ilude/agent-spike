"""Writing styles service for customizing LLM output behavior.

Provides preset writing styles that modify the system prompt to adjust
the LLM's output format, tone, and level of detail.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class StyleId(str, Enum):
    """Available writing style identifiers."""

    DEFAULT = "default"
    CONCISE = "concise"
    DETAILED = "detailed"
    FORMAL = "formal"
    CASUAL = "casual"
    TECHNICAL = "technical"
    CREATIVE = "creative"
    EDUCATIONAL = "educational"


class WritingStyle(BaseModel):
    """A writing style preset definition."""

    id: StyleId
    name: str
    description: str
    system_prompt_modifier: str = Field(
        description="Text to prepend to the system prompt"
    )
    icon: str = Field(default="", description="Optional icon/emoji for UI display")


# Preset style definitions
PRESET_STYLES: dict[StyleId, WritingStyle] = {
    StyleId.DEFAULT: WritingStyle(
        id=StyleId.DEFAULT,
        name="Default",
        description="Balanced responses with natural tone",
        system_prompt_modifier="",  # No modifier - use default behavior
        icon="",
    ),
    StyleId.CONCISE: WritingStyle(
        id=StyleId.CONCISE,
        name="Concise",
        description="Brief, to-the-point responses",
        system_prompt_modifier="""STYLE INSTRUCTION: Be concise and direct.
- Use short sentences and paragraphs
- Get to the point quickly
- Avoid unnecessary elaboration
- Use bullet points when listing items
- Skip pleasantries and filler phrases""",
        icon="",
    ),
    StyleId.DETAILED: WritingStyle(
        id=StyleId.DETAILED,
        name="Detailed",
        description="Comprehensive responses with thorough explanations",
        system_prompt_modifier="""STYLE INSTRUCTION: Provide detailed, comprehensive responses.
- Explain concepts thoroughly with context and background
- Include relevant examples and analogies
- Break down complex topics into clear sections
- Anticipate follow-up questions and address them
- Provide caveats and edge cases when relevant""",
        icon="",
    ),
    StyleId.FORMAL: WritingStyle(
        id=StyleId.FORMAL,
        name="Formal",
        description="Professional tone suitable for business contexts",
        system_prompt_modifier="""STYLE INSTRUCTION: Use formal, professional language.
- Maintain a polished, business-appropriate tone
- Avoid contractions, slang, and colloquialisms
- Structure responses with clear organization
- Use precise terminology
- Be respectful and measured in tone""",
        icon="",
    ),
    StyleId.CASUAL: WritingStyle(
        id=StyleId.CASUAL,
        name="Casual",
        description="Friendly, conversational tone",
        system_prompt_modifier="""STYLE INSTRUCTION: Be casual and conversational.
- Use a friendly, approachable tone
- Feel free to use contractions and everyday language
- Add personality while staying helpful
- Keep it relaxed but still informative
- Use humor when appropriate""",
        icon="",
    ),
    StyleId.TECHNICAL: WritingStyle(
        id=StyleId.TECHNICAL,
        name="Technical",
        description="Precise technical language for developers and experts",
        system_prompt_modifier="""STYLE INSTRUCTION: Use precise technical language.
- Assume technical familiarity with the subject
- Use proper terminology without over-explaining basics
- Include code examples when relevant
- Reference documentation, specifications, or standards
- Be accurate about technical details and limitations""",
        icon="",
    ),
    StyleId.CREATIVE: WritingStyle(
        id=StyleId.CREATIVE,
        name="Creative",
        description="Imaginative and expressive writing style",
        system_prompt_modifier="""STYLE INSTRUCTION: Be creative and expressive.
- Use vivid language and engaging descriptions
- Incorporate metaphors and analogies creatively
- Show personality and originality
- Experiment with structure when appropriate
- Make the content memorable and interesting""",
        icon="",
    ),
    StyleId.EDUCATIONAL: WritingStyle(
        id=StyleId.EDUCATIONAL,
        name="Educational",
        description="Clear explanations optimized for learning",
        system_prompt_modifier="""STYLE INSTRUCTION: Optimize for learning and understanding.
- Start with fundamentals before advanced concepts
- Use clear, progressive explanations
- Include practical examples that reinforce concepts
- Highlight key takeaways and important points
- Check understanding by summarizing main ideas
- Suggest next steps for continued learning""",
        icon="",
    ),
}


class StylesService:
    """Service for managing writing styles."""

    def list_styles(self) -> list[WritingStyle]:
        """List all available writing styles.

        Returns:
            List of all preset styles
        """
        return list(PRESET_STYLES.values())

    def get_style(self, style_id: str) -> Optional[WritingStyle]:
        """Get a specific writing style by ID.

        Args:
            style_id: The style identifier (string or StyleId enum)

        Returns:
            The style or None if not found
        """
        try:
            enum_id = StyleId(style_id)
            return PRESET_STYLES.get(enum_id)
        except ValueError:
            return None

    def get_system_prompt_modifier(self, style_id: str) -> str:
        """Get the system prompt modifier for a style.

        Convenience method for chat integration.

        Args:
            style_id: The style identifier

        Returns:
            The system prompt modifier text, or empty string for default/unknown
        """
        style = self.get_style(style_id)
        if style:
            return style.system_prompt_modifier
        return ""

    def apply_style_to_prompt(
        self, base_prompt: str, style_id: str, separator: str = "\n\n"
    ) -> str:
        """Apply a style modifier to a base system prompt.

        Args:
            base_prompt: The original system prompt
            style_id: The style to apply
            separator: Text to insert between style modifier and base prompt

        Returns:
            Modified system prompt with style applied
        """
        modifier = self.get_system_prompt_modifier(style_id)
        if not modifier:
            return base_prompt
        return f"{modifier}{separator}{base_prompt}"


# Singleton instance
_service: Optional[StylesService] = None


def get_styles_service() -> StylesService:
    """Get or create the styles service singleton."""
    global _service
    if _service is None:
        _service = StylesService()
    return _service
