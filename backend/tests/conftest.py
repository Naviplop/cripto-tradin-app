import asyncio
import os
import tempfile
import time

import pytest

os.environ.setdefault("LICENSE_SECRET", "test-secret-key")


@pytest.fixture
def temp_db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    if os.path.exists(path):
        os.remove(path)
    yield path
    if os.path.exists(path):
        for _ in range(5):
            try:
                os.remove(path)
                break
            except PermissionError:
                time.sleep(0.05)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
