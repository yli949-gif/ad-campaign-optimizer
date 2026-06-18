"""
DemoDSL YAML config generator.

Converts a VideoDemoRequest into a valid DemoDSL 2.4.1 YAML configuration.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from .schemas import VideoDemoRequest, DemoStep


class ConfigGenerator:
    """
    Generates DemoDSL YAML configurations from VideoDemoRequest objects.

    Uses conservative defaults suitable for internal demos:
    - Silent mode by default (no TTS unless explicitly requested)
    - Basic browser automation (Chrome)
    - Minimal effects (none by default)
    - Standard MP4 output
    """

    def __init__(self, output_dir: str = "output/configs"):
        """
        Initialize config generator.

        Args:
            output_dir: Directory where generated configs will be saved
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, request: VideoDemoRequest) -> str:
        """
        Generate DemoDSL YAML config from request.

        Args:
            request: VideoDemoRequest with demo parameters

        Returns:
            Path to generated YAML config file

        Raises:
            ValueError: If request validation fails
        """
        # Generate unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        config_path = self.output_dir / f"demo_{timestamp}.yaml"

        # Build DemoDSL config structure
        config = self._build_config(request)

        # Write YAML to file
        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        return str(config_path)

    def _build_config(self, request: VideoDemoRequest) -> dict[str, Any]:
        """
        Build DemoDSL config dictionary from request.

        Args:
            request: VideoDemoRequest object

        Returns:
            Dictionary representing DemoDSL config structure
        """
        config: dict[str, Any] = {}

        # Metadata section
        config["metadata"] = {
            "title": request.title,
        }

        # Voice section (only if not silent)
        if request.voice_mode != "silent":
            config["voice"] = {
                "engine": request.voice_mode,
                "voice_id": "en" if request.voice_mode == "gtts" else "default",
            }

        # Scenarios section
        config["scenarios"] = [
            self._build_scenario(request)
        ]

        # Pipeline section
        config["pipeline"] = self._build_pipeline(request)

        return config

    def _build_scenario(self, request: VideoDemoRequest) -> dict[str, Any]:
        """
        Build scenario section from request.

        Args:
            request: VideoDemoRequest object

        Returns:
            Scenario dictionary for DemoDSL config
        """
        scenario: dict[str, Any] = {
            "name": "Main Demo",
            "url": request.target_url,
            "browser": "chrome",  # DemoDSL uses "chrome" not "chromium"
            "viewport": {
                "width": request.viewport.width,
                "height": request.viewport.height,
            },
            "steps": [
                self._convert_step(step) for step in request.demo_steps
            ],
        }

        return scenario

    def _convert_step(self, step: DemoStep) -> dict[str, Any]:
        """
        Convert DemoStep to DemoDSL step format.

        Args:
            step: DemoStep object

        Returns:
            Dictionary representing DemoDSL step
        """
        demodsl_step: dict[str, Any] = {
            "action": step.action,
        }

        # Add action-specific parameters
        if step.url:
            demodsl_step["url"] = step.url
        if step.selector:
            demodsl_step["locator"] = {
                "type": "css",
                "value": step.selector,
            }
        if step.value:
            demodsl_step["value"] = step.value
        if step.direction:
            demodsl_step["direction"] = step.direction
        if step.pixels:
            demodsl_step["pixels"] = step.pixels
        if step.timeout:
            demodsl_step["timeout"] = step.timeout
        if step.filename:
            demodsl_step["filename"] = step.filename

        # Add optional common fields
        if step.narration:
            demodsl_step["narration"] = step.narration
        if step.wait is not None:
            demodsl_step["wait"] = step.wait

        return demodsl_step

    def _build_pipeline(self, request: VideoDemoRequest) -> list[dict[str, Any]]:
        """
        Build pipeline stages.

        Conservative pipeline with minimal stages:
        - generate_narration (if voice enabled)
        - optimize (final encoding)

        Args:
            request: VideoDemoRequest object

        Returns:
            List of pipeline stage dictionaries
        """
        pipeline: list[dict[str, Any]] = []

        # Add narration stage if voice enabled
        if request.voice_mode != "silent":
            pipeline.append({"generate_narration": {}})

        # Always add optimize stage for final encoding
        pipeline.append({
            "optimize": {
                "format": request.output_format,
            }
        })

        return pipeline

    def validate_config(self, config_path: str) -> bool:
        """
        Validate generated config is valid YAML.

        Args:
            config_path: Path to YAML config file

        Returns:
            True if valid, False otherwise
        """
        try:
            with open(config_path) as f:
                yaml.safe_load(f)
            return True
        except Exception:
            return False
