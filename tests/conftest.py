import pytest

from database import db as db_module
import app as app_module


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "test.db"))
    db_module.init_db()
    app_module.app.confi
    
    
    
    

    g["TESTING"] = True
    with app_module.app.test_client() as test_client:
        yield test_client
