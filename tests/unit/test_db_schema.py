"""Schema-level regressions for ORM metadata."""

from cortex_db.models import JobModel
from sqlalchemy import String


def test_job_target_id_can_store_long_parse_locators() -> None:
    target_type = JobModel.__table__.c.target_id.type

    assert isinstance(target_type, String)
    assert target_type.length == 2048
