# 业务失败时抛统一异常（用户名已存在、密码错误等）
from enum import IntEnum


class ErrorCode(IntEnum):
    SUCCESS = 200
    INVALID_PARAMS = 1001
    UNAUTHORIZED = 1002
    FORBIDDEN = 1003
    NOT_FOUND = 1004
    INTERNAL_ERROR = 1999

    USERNAME_EXISTS = 2001
    PHONE_EXISTS = 2002
    USER_NOT_FOUND = 2003
    WRONG_PASSWORD = 2004


class BusinessException(Exception):
    def __init__(self, error_code: ErrorCode, detail: str = ""):
        self.error_code = error_code
        self.detail = detail or error_code.name
        super().__init__(self.detail)