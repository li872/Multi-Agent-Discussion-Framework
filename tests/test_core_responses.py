from backend.core.exceptions import ErrorCode
from backend.core.responses import Result
from backend.core.exception_handlers import _http_status


def test_should_return_payload_when_result_ok():
    r = Result.ok({"id": "1"})
    assert r.code == 200
    assert r.message == "success"
    assert r.data == {"id": "1"}


def test_should_set_data_none_when_result_fail():
    r = Result.fail(4001, "Discussion not found")
    assert r.code == 4001
    assert r.data is None
    dumped = r.model_dump()
    assert dumped["message"] == "Discussion not found"


def test_should_map_http_status_for_auth_and_not_found():
    assert _http_status(ErrorCode.UNAUTHORIZED) == 401
    assert _http_status(ErrorCode.USER_NOT_FOUND) == 404
    assert _http_status(ErrorCode.USERNAME_EXISTS) == 409
    assert _http_status(ErrorCode.WRONG_PASSWORD) == 400
