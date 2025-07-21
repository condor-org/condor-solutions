# backend/tests/conftest.py
import pytest
from django.conf import settings

class DisableMigrations:
    """Deshabilita todas las migraciones."""
    def __contains__(self, item):
        return True
    def __getitem__(self, item):
        return None

@pytest.fixture(autouse=True)
def disable_migrations(monkeypatch):
    """Fixture que parchea settings.MIGRATION_MODULES para desactivar migraciones."""
    monkeypatch.setattr(settings, "MIGRATION_MODULES", DisableMigrations())
