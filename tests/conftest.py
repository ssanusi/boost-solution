import pytest
import fakeredis
from unittest.mock import patch

@pytest.fixture(autouse=True)
def mock_redis():
    """Mock redis.from_url to return a fakeredis client."""
    fake_redis = fakeredis.FakeRedis(decode_responses=True)
    with patch("redis.from_url", return_value=fake_redis):
        yield fake_redis
