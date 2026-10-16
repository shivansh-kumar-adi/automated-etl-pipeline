from datetime import datetime, timezone

from src.transform import transform_post
from src.validate import PostInput


def test_transform_normalizes_whitespace():
    now = datetime.now(timezone.utc)
    result = transform_post(PostInput(id=1, userId=2, title="  hello   world ", body="a\n b"), now)
    assert result["title"] == "hello world"
    assert result["body"] == "a b"
    assert result["user_id"] == 2
    assert result["ingested_at"] is now
