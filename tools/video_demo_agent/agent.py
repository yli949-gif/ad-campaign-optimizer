#!/usr/bin/env python3
"""
Entry point script for Video Demo Agent.

This wrapper allows the agent to be run as a standalone script.
"""

import sys
from pathlib import Path

# Add video_demo_agent package to path
sys.path.insert(0, str(Path(__file__).parent))

from video_demo_agent.agent import main

if __name__ == "__main__":
    main()
