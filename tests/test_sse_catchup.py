import pytest

from backend.core.exceptions import ErrorCode
from backend.core.exception_handlers import _http_status
from backend.services.realtime.catchup import catchup_mode, chunk_items
from backend.services.realtime.sse_manager import claim_stream, release_stream


def test_should_map_skill_not_found_to_404():
    assert _http_status(ErrorCode.SKILL_NOT_FOUND) == 404


def test_should_use_each_mode_when_at_most_20():
    assert catchup_mode(0) == "each"
    assert catchup_mode(20) == "each"


def test_should_use_batch_mode_when_between_21_and_200():
    assert catchup_mode(21) == "batch"
    assert catchup_mode(200) == "batch"


def test_should_use_summary_mode_when_over_200():
    assert catchup_mode(201) == "summary"


def test_should_split_catchup_into_batches_of_20():
    items = list(range(45))
    batches = chunk_items(items, 20)
    assert len(batches) == 3
    assert batches[0] == list(range(20))
    assert batches[-1] == list(range(40, 45))


@pytest.mark.asyncio
async def test_should_cancel_previous_sse_for_same_user_discussion():
    first = await claim_stream("d1", "u1")
    assert first.is_set() is False
    second = await claim_stream("d1", "u1")
    assert first.is_set() is True
    assert second.is_set() is False
    await release_stream("d1", "u1", second)
