from __future__ import annotations

from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator
)


Tag = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=3,
        max_length=30
    )
]


class PlannerProposal(BaseModel):
    """Validated structured output produced by Planner."""

    model_config = ConfigDict(
        extra="forbid"
    )

    tags: list[Tag] = Field(
        min_length=3,
        max_length=3
    )

    summary: str = Field(
        min_length=1
    )

    @field_validator("tags")
    @classmethod
    def tags_must_be_distinct(
        cls,
        tags: list[str]
    ) -> list[str]:
        """Require three different tags."""

        normalized = [
            tag.casefold()
            for tag in tags
        ]

        if len(set(normalized)) != 3:
            raise ValueError(
                "All three tags must be distinct."
            )

        return tags

    @field_validator("summary")
    @classmethod
    def summary_must_have_at_most_25_words(
        cls,
        summary: str
    ) -> str:
        """Enforce the assignment's 25-word maximum."""

        cleaned = " ".join(
            summary.split()
        )

        word_count = len(
            cleaned.split()
        )

        if word_count > 25:
            raise ValueError(
                "Summary must contain no more than "
                f"25 words; received {word_count}."
            )

        return cleaned


class ReviewerFeedback(BaseModel):
    """Structured decision produced by Reviewer."""

    model_config = ConfigDict(
        extra="forbid"
    )

    approved: bool
    issues: list[str] = Field(
        default_factory=list
    )

    @field_validator("issues")
    @classmethod
    def clean_issues(
        cls,
        issues: list[str]
    ) -> list[str]:
        """Remove blank reviewer issues."""

        return [
            issue.strip()
            for issue in issues
            if issue.strip()
        ]