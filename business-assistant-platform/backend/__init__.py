"""
File: backend/__init__.py
Purpose: Marks the backend source root as a concrete Python package.

Why this exists:
- Prevents import ambiguity with similarly named third-party packages.
- Ensures Uvicorn can reliably import `backend.api.main:app` inside containers.
"""

