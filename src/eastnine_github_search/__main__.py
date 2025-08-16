#!/usr/bin/env python3
"""
Entry point for running the EastNine GitHub Search MCP server as a module.

Usage:
    python -m src.eastnine_github_search
"""

from .server import main

if __name__ == "__main__":
    main()
