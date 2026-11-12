"""Imports every model module so metadata is complete for Alembic and tests."""

from app.database.base import Base  # noqa: F401
from app.modules.assessments import models as _assessments  # noqa: F401
from app.modules.auth import models as _auth  # noqa: F401
from app.modules.phase_management import models as _phase  # noqa: F401
