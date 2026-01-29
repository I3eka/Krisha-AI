#!/usr/bin/env python
"""Entry point for Chainlit web interface.

This file re-exports all symbols from the actual implementation
so that `chainlit run app.py` picks up the decorators.
"""

from src.interfaces.web.chat import *  # noqa: F401, F403
