"""Central configuration, loaded from environment / .env."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    database_url: str = "mysql+pymysql://mtadmin:change_me@localhost:3306/mt_access?charset=utf8mb4"
    secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    bcrypt_rounds: int = 12
    max_failed_logins: int = 5
    lockout_minutes: int = 15
    allowed_app_roots: str = r"C:\Trading"
    cors_origins: str = "http://localhost:5173"
    initial_admin_email: str = ""
    initial_admin_password: str = ""
    agent_secret: str = ""
    agent_online_seconds: int = 30
    launch_timeout_seconds: int = 60
    # Apache Guacamole
    guac_internal_url: str = "http://127.0.0.1:8080/guacamole"
    guac_json_secret_key: str = ""
    guac_token_ttl_seconds: int = 60
    # Encrypted Windows RDP credentials
    rdp_credential_encryption_key: str = ""
    rdp_allowed_remote_app_aliases: str = "MT4,MT5"
    
settings = Settings()
