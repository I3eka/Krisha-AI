#!/usr/bin/env python
"""Entry point for CLI console interface."""

import asyncio
from src.interfaces.cli.console import main

if __name__ == "__main__":
    asyncio.run(main())
