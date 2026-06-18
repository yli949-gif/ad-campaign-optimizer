"""
DemoDSL subprocess runner.

Provides a safe wrapper around the demodsl CLI command, capturing output and
detecting common errors.
"""

import subprocess
import time
from pathlib import Path
from typing import Optional


class DemoDSLRunner:
    """
    Safe subprocess wrapper for DemoDSL CLI.

    Executes `demodsl run <config>` and captures stdout/stderr, detecting
    common error conditions without crashing.
    """

    def __init__(self, venv_path: Optional[str] = None):
        """
        Initialize DemoDSL runner.

        Args:
            venv_path: Path to virtual environment (defaults to .venv in current dir)
        """
        if venv_path:
            self.venv_path = Path(venv_path)
        else:
            # Default to .venv in tools/video_demo_agent/
            self.venv_path = Path(__file__).parent.parent / ".venv"

        self.demodsl_bin = self.venv_path / "bin" / "demodsl"

    def run(
        self,
        config_path: str,
        output_dir: Optional[str] = None,
        timeout: int = 300,
    ) -> dict[str, any]:
        """
        Run DemoDSL with the given config.

        Args:
            config_path: Path to DemoDSL YAML config file
            output_dir: Optional output directory override
            timeout: Timeout in seconds (default: 300 = 5 minutes)

        Returns:
            Dictionary with:
                - success (bool): Whether execution succeeded
                - stdout (str): Standard output
                - stderr (str): Standard error
                - return_code (int): Process return code
                - duration_seconds (float): Execution time
                - output_video (str | None): Path to generated video if found
                - errors (list[str]): Detected error messages
        """
        start_time = time.time()
        result = {
            "success": False,
            "stdout": "",
            "stderr": "",
            "return_code": -1,
            "duration_seconds": 0.0,
            "output_video": None,
            "errors": [],
        }

        # Check if demodsl binary exists
        if not self.demodsl_bin.exists():
            result["errors"].append(
                f"DemoDSL not found at: {self.demodsl_bin}. "
                "Ensure virtual environment is set up correctly."
            )
            return result

        # Build command
        cmd = [str(self.demodsl_bin), "run", config_path]
        if output_dir:
            cmd.extend(["--output-dir", output_dir])

        try:
            # Run subprocess
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            result["stdout"] = process.stdout
            result["stderr"] = process.stderr
            result["return_code"] = process.returncode
            result["duration_seconds"] = time.time() - start_time

            # Check for success
            if process.returncode == 0:
                result["success"] = True

                # Try to extract output video path from stdout
                output_video = self._extract_output_path(process.stdout)
                if output_video:
                    result["output_video"] = output_video
            else:
                # Execution failed - detect common errors
                result["errors"] = self._detect_errors(
                    process.stdout,
                    process.stderr,
                    process.returncode
                )

        except subprocess.TimeoutExpired:
            result["duration_seconds"] = time.time() - start_time
            result["errors"].append(
                f"DemoDSL execution timed out after {timeout} seconds. "
                "Try reducing the number of demo steps or increasing viewport size."
            )

        except FileNotFoundError:
            result["errors"].append(
                f"Command not found: {self.demodsl_bin}. "
                "Check that DemoDSL is installed in the virtual environment."
            )

        except Exception as e:
            result["duration_seconds"] = time.time() - start_time
            result["errors"].append(f"Unexpected error running DemoDSL: {str(e)}")

        return result

    def validate_config(self, config_path: str) -> dict[str, any]:
        """
        Validate DemoDSL config without running.

        Args:
            config_path: Path to DemoDSL YAML config file

        Returns:
            Dictionary with:
                - valid (bool): Whether config is valid
                - stdout (str): Validation output
                - stderr (str): Validation errors
                - errors (list[str]): Detected error messages
        """
        result = {
            "valid": False,
            "stdout": "",
            "stderr": "",
            "errors": [],
        }

        if not self.demodsl_bin.exists():
            result["errors"].append(f"DemoDSL not found at: {self.demodsl_bin}")
            return result

        try:
            process = subprocess.run(
                [str(self.demodsl_bin), "validate", config_path],
                capture_output=True,
                text=True,
                timeout=30,
            )

            result["stdout"] = process.stdout
            result["stderr"] = process.stderr

            if process.returncode == 0:
                result["valid"] = True
            else:
                result["errors"] = self._detect_errors(
                    process.stdout,
                    process.stderr,
                    process.returncode
                )

        except subprocess.TimeoutExpired:
            result["errors"].append("Config validation timed out after 30 seconds")

        except Exception as e:
            result["errors"].append(f"Error validating config: {str(e)}")

        return result

    def _extract_output_path(self, stdout: str) -> Optional[str]:
        """
        Extract output video path from DemoDSL stdout.

        Args:
            stdout: Standard output from demodsl run

        Returns:
            Path to output video file, or None if not found
        """
        # DemoDSL prints "Done → <path>" at the end
        for line in stdout.splitlines():
            if line.startswith("Done →"):
                parts = line.split("→", 1)
                if len(parts) == 2:
                    return parts[1].strip()

            # Also check for "Final output:" lines
            if "Final output:" in line:
                parts = line.split("Final output:", 1)
                if len(parts) == 2:
                    return parts[1].strip()

        return None

    def _detect_errors(self, stdout: str, stderr: str, return_code: int) -> list[str]:
        """
        Detect common error conditions from output.

        Args:
            stdout: Standard output
            stderr: Standard error
            return_code: Process return code

        Returns:
            List of detected error messages
        """
        errors = []

        combined = stdout + "\n" + stderr

        # Check for common error patterns
        if "ModuleNotFoundError" in combined:
            if "gtts" in combined:
                errors.append(
                    "Google TTS (gtts) module not installed. "
                    "Install with: pip install gtts"
                )
            else:
                errors.append("Missing Python module. Check stderr for details.")

        if "playwright" in combined.lower() and "not found" in combined.lower():
            errors.append(
                "Playwright browser not installed. "
                "Run: playwright install chromium"
            )

        if "ffmpeg" in combined.lower() and ("not found" in combined.lower() or "command not found" in combined.lower()):
            errors.append(
                "FFmpeg not found. Install with: brew install ffmpeg (macOS)"
            )

        if "ValidationError" in combined:
            errors.append(
                "DemoDSL config validation failed. Check the YAML structure matches DemoDSL schema."
            )

        if "TimeoutError" in combined or "timeout" in combined.lower():
            errors.append(
                "Browser operation timed out. Try increasing wait times in demo steps."
            )

        if "ConnectionError" in combined or "connection refused" in combined.lower():
            errors.append(
                "Cannot connect to target URL. Check that the URL is accessible."
            )

        # Generic error if nothing specific detected
        if not errors and return_code != 0:
            errors.append(
                f"DemoDSL exited with code {return_code}. Check stdout/stderr for details."
            )

        return errors
