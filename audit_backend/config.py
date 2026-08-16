# 审计后端配置：独立 JWT，事件通过主后端 admin 接口读取
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class AuditSettings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    audit_jwt_secret: str = "change-me-audit-jwt"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 240

    audit_admin_username: str = "admin"
    audit_admin_password: str = "audit123"

    # 主系统管理接口，与 backend.config.admin_token 使用同一把钥匙
    main_api_base: str = "http://localhost:8000"
    admin_jwt_secret: str = ""
    admin_token: str = ""


settings = AuditSettings()
