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

    # ── 角色模块 3000-3999 ──
    SKILL_NOT_FOUND = 3001
    SKILL_NAME_EXISTS = 3004

    # 查不到讨论时用错误码
    DISCUSSION_NOT_FOUND = 4001
    DISCUSSION_INVALID_STATUS = 4002

class BusinessException(Exception):
    def __init__(self, error_code: ErrorCode, detail: str = ""):
        self.error_code = error_code
        self.detail = detail or error_code.name
        super().__init__(self.detail)