import os
import tempfile
import atexit

import pytest
from httpx import AsyncClient

# Ensure tests use a temporary SQLite database and don't run startup seeding
tmpdir = tempfile.mkdtemp(prefix="semantic_text_search_test_")
db_path = os.path.join(tmpdir, "test.db")
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
os.environ.setdefault("SEED_ON_STARTUP", "False")


def _cleanup_tmpdir() -> None:
    try:
        import shutil

        shutil.rmtree(tmpdir)
    except Exception:
        pass

atexit.register(_cleanup_tmpdir)


@pytest.fixture(scope="session", autouse=True)
async def setup_database():
    import app.models
    from app.database import Base, engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    from app.main import app

    async with AsyncClient(app=app, base_url="http://testserver") as ac:
        yield ac
