"""
Pydantic schemas for Video Demo Agent.

Defines input (VideoDemoRequest, DemoStep) and output (VideoDemoResult) models
for the video demo generation workflow.
"""

from typing import Literal, Optional, Any
from pydantic import BaseModel, Field, field_validator


class Viewport(BaseModel):
    """Browser viewport dimensions."""

    width: int = Field(default=1280, gt=0, le=3840, description="Viewport width in pixels")
    height: int = Field(default=720, gt=0, le=2160, description="Viewport height in pixels")


class DemoStep(BaseModel):
    """
    A single step in the demo workflow.

    Represents one action (navigate, click, type, etc.) with optional narration.
    """

    action: Literal[
        "navigate",
        "click",
        "type",
        "scroll",
        "wait_for",
        "screenshot",
    ] = Field(..., description="Action type to perform")

    # Action-specific parameters
    url: Optional[str] = Field(None, description="URL to navigate to (for navigate action)")
    selector: Optional[str] = Field(None, description="CSS selector for element targeting")
    value: Optional[str] = Field(None, description="Text value to type (for type action)")
    direction: Optional[Literal["up", "down", "left", "right"]] = Field(
        None, description="Scroll direction (for scroll action)"
    )
    pixels: Optional[int] = Field(None, gt=0, description="Pixels to scroll (for scroll action)")
    timeout: Optional[float] = Field(None, gt=0, le=30.0, description="Timeout in seconds")
    filename: Optional[str] = Field(None, description="Screenshot filename (for screenshot action)")

    # Common optional fields
    narration: Optional[str] = Field(None, description="Voice-over narration text for this step")
    wait: Optional[float] = Field(1.0, ge=0, le=10.0, description="Seconds to wait after action")

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        """Validate action is supported."""
        valid_actions = {"navigate", "click", "type", "scroll", "wait_for", "screenshot"}
        if v not in valid_actions:
            raise ValueError(f"Action must be one of: {', '.join(valid_actions)}")
        return v

    def model_post_init(self, __context: Any) -> None:
        """Validate action-specific required fields after initialization."""
        if self.action == "navigate" and not self.url:
            raise ValueError("navigate action requires 'url' field")
        if self.action == "click" and not self.selector:
            raise ValueError("click action requires 'selector' field")
        if self.action == "type" and (not self.selector or not self.value):
            raise ValueError("type action requires 'selector' and 'value' fields")
        if self.action == "scroll" and not self.direction:
            raise ValueError("scroll action requires 'direction' field")
        if self.action == "wait_for" and not self.selector:
            raise ValueError("wait_for action requires 'selector' field")


class VideoDemoRequest(BaseModel):
    """
    Request to generate a video demo.

    Contains all parameters needed to generate a DemoDSL config and optionally
    execute it to produce a demo video.
    """

    title: str = Field(..., min_length=1, max_length=200, description="Demo video title")
    target_url: str = Field(..., description="Base URL for the demo")
    demo_steps: list[DemoStep] = Field(
        ..., min_length=1, description="List of demo actions to perform"
    )

    viewport: Viewport = Field(default_factory=Viewport, description="Browser viewport size")
    output_format: Literal["mp4", "webm", "gif"] = Field(
        default="mp4", description="Output video format"
    )
    voice_mode: Literal["silent", "gtts"] = Field(
        default="silent",
        description="Voice narration mode: silent (no voice) or gtts (Google TTS)"
    )
    output_dir: str = Field(default="output", description="Output directory for generated files")

    @field_validator("target_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("target_url must start with http:// or https://")
        return v

    @field_validator("demo_steps")
    @classmethod
    def validate_steps(cls, v: list[DemoStep]) -> list[DemoStep]:
        """Validate demo steps list is not empty."""
        if not v:
            raise ValueError("demo_steps cannot be empty")
        return v


class VideoDemoResult(BaseModel):
    """
    Result of video demo generation.

    Contains status, paths to generated artifacts, logs, and any errors encountered.
    """

    status: Literal["success", "config_generated", "failed"] = Field(
        ..., description="Overall status of the operation"
    )
    config_path: Optional[str] = Field(None, description="Path to generated DemoDSL YAML config")
    video_path: Optional[str] = Field(None, description="Path to generated video file")

    logs: list[str] = Field(default_factory=list, description="Execution logs and output")
    errors: list[str] = Field(default_factory=list, description="Error messages if any")

    duration_seconds: Optional[float] = Field(None, ge=0, description="Total execution time")
    video_duration_seconds: Optional[float] = Field(None, ge=0, description="Generated video duration")

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "status": "success",
                "config_path": "output/configs/demo_20260618_142630.yaml",
                "video_path": "output/videos/demo_20260618_142630.mp4",
                "logs": [
                    "Generated config: demo_20260618_142630.yaml",
                    "Running DemoDSL...",
                    "Video generated successfully"
                ],
                "errors": [],
                "duration_seconds": 45.3,
                "video_duration_seconds": 12.5
            }
        }
