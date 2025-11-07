# ================================================================
# File: __init__.py
# Path: app/models/__init__.py
# Description: Exposes the SQLAlchemy declarative base for SacredFlow models.
# Author: Clint Johnson
# Project: SacredFlow API
# ================================================================

from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Lazily expose models for Alembic / metadata discovery
from app.models.communication import Communication  # noqa: E402,F401
from app.models.checkout import SquareCheckoutLink  # noqa: E402,F401
