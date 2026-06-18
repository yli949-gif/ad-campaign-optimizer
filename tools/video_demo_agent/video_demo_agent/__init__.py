"""
Video Demo Agent - DemoDSL 2.4.1 wrapper for generating product demo videos.

This package provides a minimal internal agent that converts simple JSON requests
into DemoDSL YAML configurations and optionally executes them to generate demo videos.
"""

from .schemas import VideoDemoRequest, DemoStep, VideoDemoResult
from .config_generator import ConfigGenerator
from .runner import DemoDSLRunner

__version__ = "0.1.0"
__all__ = [
    "VideoDemoRequest",
    "DemoStep",
    "VideoDemoResult",
    "ConfigGenerator",
    "DemoDSLRunner",
]
