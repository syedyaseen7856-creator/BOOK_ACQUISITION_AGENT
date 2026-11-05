import os
import shutil
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Set testing environment variables before importing app
os.environ["APP_ENV"] = "testing"
os.environ["SEARCH_PROVIDER"] = "mock"
os.environ["DEBUG"] = "false"

test_tmp_base = Path(__file__).resolve().parent.parent / "data" / "test_tmp"
test_tmp_base.mkdir(parents=True, exist_ok=True)
temp_storage = tempfile.mkdtemp(prefix="syll_test_data_", dir=str(test_tmp_base))
os.environ["STORAGE_DIR"] = temp_storage


from app.config import settings
from app.db.session import init_db
from app.main import app

# Initialize DB in temporary directory
init_db()


@pytest.fixture(scope="session", autouse=True)
def cleanup_temp_storage():
    yield
    if Path(temp_storage).exists():
        shutil.rmtree(temp_storage, ignore_errors=True)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
