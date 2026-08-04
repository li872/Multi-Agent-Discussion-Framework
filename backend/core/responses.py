# 所有接口返回统一长这样 {code, message, data}
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Result(BaseModel, Generic[T]):
    code: int
    message: str = "success"
    data: T | None = None

    @classmethod
    def ok(cls, data: T, message: str = "success") -> "Result[T]":
        return cls(code=200, message=message, data=data)

    @classmethod
    def fail(cls, code: int, message: str) -> "Result[Any]":
        return cls(code=code, message=message, data=None)