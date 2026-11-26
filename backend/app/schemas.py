"""Pydantic request/response models."""
import re
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from .security import check_password_policy

CLIENT_CODE_RE = re.compile(r"^[A-Z0-9_-]{3,32}$")


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- auth ----------
class LoginIn(BaseModel):
    email: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _pw(cls, v):
        return check_password_policy(v)

class UserOut(ORM):
    id: int
    client_code: Optional[str]
    name: str
    email: str
    role: str
    status: str
    created_at: datetime


# ---------- applications ----------
class ApplicationCreate(BaseModel):
    application_name: str = Field(min_length=1, max_length=120)
    application_type: Literal["MT4", "MT5"]
    executable_path: str = Field(min_length=1, max_length=500)
    working_directory: Optional[str] = Field(default=None, max_length=500)
    status: Literal["active", "inactive"] = "active"


class ApplicationUpdate(BaseModel):
    application_name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    application_type: Optional[Literal["MT4", "MT5"]] = None
    executable_path: Optional[str] = Field(default=None, min_length=1, max_length=500)
    working_directory: Optional[str] = Field(default=None, max_length=500)
    status: Optional[Literal["active", "inactive"]] = None


class ApplicationOut(ORM):
    id: int
    application_name: str
    application_type: str
    executable_path: str
    working_directory: str
    status: str
    created_at: datetime


# ---------- assignments ----------
class AssignmentCreate(BaseModel):
    client_id: int
    application_id: int


class AssignmentUpdate(BaseModel):
    application_id: int


class AssignmentOut(ORM):
    id: int
    client_id: int
    application_id: int
    assigned_at: datetime
    application: ApplicationOut


# ---------- clients ----------
class ClientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    client_code: Optional[str] = None            # auto-generated (CLIENT###) if omitted
    password: Optional[str] = None               # auto-generated if omitted

    @field_validator("client_code")
    @classmethod
    def _code(cls, v):
        if v is None:
            return v
        v = v.strip().upper()
        if not CLIENT_CODE_RE.match(v):
            raise ValueError("client_code must be 3-32 chars: A-Z, 0-9, _ or -")
        return v

    @field_validator("password")
    @classmethod
    def _pw(cls, v):
        return None if v is None else check_password_policy(v)


class ClientUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    email: Optional[EmailStr] = None
    status: Optional[Literal["active", "inactive"]] = None


class PasswordReset(BaseModel):
    new_password: Optional[str] = None           # auto-generated if omitted

    @field_validator("new_password")
    @classmethod
    def _pw(cls, v):
        return None if v is None else check_password_policy(v)


class PasswordResetOut(BaseModel):
    generated_password: Optional[str] = None     # only present when the server generated it


class ClientOut(ORM):
    id: int
    client_code: Optional[str]
    name: str
    email: str
    status: str
    created_at: datetime
    assignment: Optional[AssignmentOut] = None


class ClientCreateOut(ClientOut):
    initial_password: Optional[str] = None       # shown exactly once, only if generated


class ActivityOut(ORM):
    id: int
    user_id: Optional[int]
    activity: str
    details: Optional[str]
    ip_address: Optional[str]
    created_at: datetime

class SessionOut(BaseModel):
    """What a CLIENT sees. Deliberately no executable path, pid or other client's data."""
    status: str
    session_id: Optional[str] = None
    application_name: Optional[str] = None
    application_type: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    message: Optional[str] = None


class SessionAdminOut(SessionOut):
    id: int
    client_id: int
    client_code: Optional[str] = None
    pid: Optional[int] = None


class AgentHeartbeat(BaseModel):
    name: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9._-]+$")
    version: Optional[str] = Field(default=None, max_length=20)


class AgentReport(BaseModel):
    status: Literal["running", "stopped", "failed"]
    pid: Optional[int] = Field(default=None, ge=1)
    message: Optional[str] = Field(default=None, max_length=255)


class AgentOut(ORM):
    id: int
    name: str
    version: Optional[str]
    last_seen: datetime
    online: bool = False

# ---------- RDP credentials ----------

class RdpCredentialCreate(BaseModel):
    hostname: str = Field(min_length=1, max_length=253)
    port: int = Field(default=3389, ge=1, le=65535)
    username: str = Field(min_length=1, max_length=500)
    password: str = Field(min_length=1, max_length=2000)
    remote_app_alias: str = Field(min_length=1, max_length=64)


class RdpCredentialOut(BaseModel):
    application_id: int
    hostname: str
    port: int
    remote_app_alias: str
    status: str
    created_at: datetime
    updated_at: datetime

class RdpViewerTokenOut(BaseModel):
    authToken: str
    username: Optional[str] = None
    dataSource: Optional[str] = None
    availableDataSources: list[str] = Field(default_factory=list)

    