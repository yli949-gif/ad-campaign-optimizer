"""
Video Demo Agent - Main orchestrator.

Coordinates config generation and DemoDSL execution from JSON requests.
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Optional

from .schemas import VideoDemoRequest, VideoDemoResult
from .config_generator import ConfigGenerator
from .runner import DemoDSLRunner


class VideoDemoAgent:
    """
    Main agent orchestrator.

    Coordinates the workflow:
    1. Load and validate request JSON
    2. Generate DemoDSL YAML config
    3. Optionally run DemoDSL to produce video
    4. Return structured result
    """

    def __init__(
        self,
        config_output_dir: str = "output/configs",
        video_output_dir: str = "output/videos",
    ):
        """
        Initialize Video Demo Agent.

        Args:
            config_output_dir: Directory for generated YAML configs
            video_output_dir: Directory for generated videos
        """
        self.config_generator = ConfigGenerator(output_dir=config_output_dir)
        self.runner = DemoDSLRunner()
        self.config_output_dir = Path(config_output_dir)
        self.video_output_dir = Path(video_output_dir)

        # Ensure output directories exist
        self.config_output_dir.mkdir(parents=True, exist_ok=True)
        self.video_output_dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        request: VideoDemoRequest,
        run_demodsl: bool = False,
    ) -> VideoDemoResult:
        """
        Generate demo config and optionally run DemoDSL.

        Args:
            request: VideoDemoRequest with demo parameters
            run_demodsl: Whether to execute DemoDSL to produce video

        Returns:
            VideoDemoResult with status, paths, logs, and errors
        """
        start_time = time.time()
        logs = []
        errors = []

        # Step 1: Generate config
        logs.append(f"Generating DemoDSL config for: {request.title}")
        try:
            config_path = self.config_generator.generate(request)
            logs.append(f"✓ Config generated: {config_path}")
        except Exception as e:
            errors.append(f"Failed to generate config: {str(e)}")
            return VideoDemoResult(
                status="failed",
                config_path=None,
                video_path=None,
                logs=logs,
                errors=errors,
                duration_seconds=time.time() - start_time,
            )

        # Step 2: Validate config
        if not self.config_generator.validate_config(config_path):
            errors.append("Generated config is not valid YAML")
            return VideoDemoResult(
                status="failed",
                config_path=config_path,
                video_path=None,
                logs=logs,
                errors=errors,
                duration_seconds=time.time() - start_time,
            )

        # If not running DemoDSL, return config-only result
        if not run_demodsl:
            logs.append("Skipping video generation (--generate-only mode)")
            return VideoDemoResult(
                status="config_generated",
                config_path=config_path,
                video_path=None,
                logs=logs,
                errors=errors,
                duration_seconds=time.time() - start_time,
            )

        # Step 3: Run DemoDSL
        logs.append("Running DemoDSL to generate video...")
        run_result = self.runner.run(
            config_path=config_path,
            output_dir=str(self.video_output_dir),
        )

        # Append DemoDSL logs
        if run_result["stdout"]:
            logs.append("--- DemoDSL Output ---")
            logs.extend(run_result["stdout"].splitlines())

        # Check for errors
        if not run_result["success"]:
            errors.extend(run_result["errors"])
            if run_result["stderr"]:
                logs.append("--- DemoDSL Errors ---")
                logs.extend(run_result["stderr"].splitlines())

            return VideoDemoResult(
                status="failed",
                config_path=config_path,
                video_path=None,
                logs=logs,
                errors=errors,
                duration_seconds=time.time() - start_time,
            )

        # Success!
        logs.append(f"✓ Video generated: {run_result['output_video']}")

        return VideoDemoResult(
            status="success",
            config_path=config_path,
            video_path=run_result["output_video"],
            logs=logs,
            errors=errors,
            duration_seconds=time.time() - start_time,
            video_duration_seconds=None,  # Could parse from DemoDSL output if needed
        )

    def generate_from_file(
        self,
        request_file: str,
        run_demodsl: bool = False,
    ) -> VideoDemoResult:
        """
        Load request from JSON file and generate demo.

        Args:
            request_file: Path to JSON request file
            run_demodsl: Whether to execute DemoDSL to produce video

        Returns:
            VideoDemoResult with status, paths, logs, and errors
        """
        # Load and parse JSON
        try:
            with open(request_file) as f:
                request_data = json.load(f)
        except FileNotFoundError:
            return VideoDemoResult(
                status="failed",
                config_path=None,
                video_path=None,
                logs=[],
                errors=[f"Request file not found: {request_file}"],
                duration_seconds=0.0,
            )
        except json.JSONDecodeError as e:
            return VideoDemoResult(
                status="failed",
                config_path=None,
                video_path=None,
                logs=[],
                errors=[f"Invalid JSON: {str(e)}"],
                duration_seconds=0.0,
            )

        # Validate request
        try:
            request = VideoDemoRequest(**request_data)
        except Exception as e:
            return VideoDemoResult(
                status="failed",
                config_path=None,
                video_path=None,
                logs=[],
                errors=[f"Invalid request format: {str(e)}"],
                duration_seconds=0.0,
            )

        # Generate
        return self.generate(request, run_demodsl=run_demodsl)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Video Demo Agent - Generate product demo videos from JSON requests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate config only (no video)
  python agent.py examples/ai_crew_demo_request.json --generate-only

  # Generate config and run DemoDSL to produce video
  python agent.py examples/ai_crew_demo_request.json --run
        """,
    )

    parser.add_argument(
        "request_file",
        help="Path to JSON request file",
    )

    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--generate-only",
        action="store_true",
        help="Generate DemoDSL config only (do not run video generation)",
    )
    mode_group.add_argument(
        "--run",
        action="store_true",
        help="Generate config and run DemoDSL to produce video",
    )

    parser.add_argument(
        "--config-output-dir",
        default="output/configs",
        help="Directory for generated YAML configs (default: output/configs)",
    )

    parser.add_argument(
        "--video-output-dir",
        default="output/videos",
        help="Directory for generated videos (default: output/videos)",
    )

    args = parser.parse_args()

    # Create agent
    agent = VideoDemoAgent(
        config_output_dir=args.config_output_dir,
        video_output_dir=args.video_output_dir,
    )

    # Run
    print(f"Video Demo Agent - Processing: {args.request_file}")
    print("-" * 60)

    result = agent.generate_from_file(
        request_file=args.request_file,
        run_demodsl=args.run,
    )

    # Print logs
    for log in result.logs:
        print(log)

    # Print errors
    if result.errors:
        print("\n❌ ERRORS:")
        for error in result.errors:
            print(f"  - {error}")

    # Print summary
    print("\n" + "=" * 60)
    print(f"Status: {result.status}")
    if result.config_path:
        print(f"Config: {result.config_path}")
    if result.video_path:
        print(f"Video:  {result.video_path}")
    print(f"Duration: {result.duration_seconds:.1f}s")
    print("=" * 60)

    # Exit code
    sys.exit(0 if result.status != "failed" else 1)


if __name__ == "__main__":
    main()
