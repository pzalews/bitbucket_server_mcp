from __future__ import annotations

from fastmcp import FastMCP
from fastmcp.prompts import Message


def register_prompts(mcp: FastMCP) -> None:

    @mcp.prompt
    def review_pull_request_prompt(
        project: str,
        repository: str,
        pr_id: str,
        review_style: str = "conventional-comments",
    ) -> list[Message]:
        """Generate a structured prompt for reviewing a Bitbucket pull request.

        review_style: conventional-comments | minimal | detailed
        """
        style_guide = {
            "conventional-comments": (
                "Use Conventional Comments format: "
                "praise:, nitpick:, suggestion:, issue:, question:, thought:, chore:, note:."
            ),
            "minimal": "Keep all feedback brief and directly actionable.",
            "detailed": "Provide thorough explanations with rationale for each comment.",
        }
        style = style_guide.get(review_style, style_guide["conventional-comments"])

        return [
            Message(
                f"Please review pull request #{pr_id} in {project}/{repository}.\n\n"
                "**Steps:**\n"
                f"1. Call `get_pull_request` with project='{project}', "
                f"repository='{repository}', pr_id={pr_id}\n"
                "2. Call `get_diff` on the same PR to read the code changes\n"
                "3. Call `get_comments` to see existing review discussion\n"
                "4. Call `get_activities` to understand the PR history\n\n"
                f"**Review style:** {style}\n\n"
                "**Focus areas:** correctness, test coverage, naming clarity, "
                "edge cases, security concerns.\n\n"
                "After reviewing:\n"
                "- Use `add_comment_inline` for specific line-level feedback\n"
                "- Use `publish_review` with your overall summary and "
                "status (APPROVED/NEEDS_WORK)"
            )
        ]
