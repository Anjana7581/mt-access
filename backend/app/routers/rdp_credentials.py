
"""Admin RDP credential management and client Guacamole access."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import require_admin, require_client
from ..models import (
    Application,
    ClientApplication,
    RdpCredential,
    User,
)
from ..schemas import (
    RdpCredentialCreate,
    RdpCredentialOut,
    RdpViewerTokenOut,
)
from ..services import audit
from ..services.credential_crypto import (
    encrypt_credential,
    decrypt_credential,
)
from ..services.guacamole import issue_rdp_token
from ..services import sessions as session_service


# Admin-only endpoints
router = APIRouter(
    prefix="/api/applications",
    tags=["RDP credentials"],
    dependencies=[Depends(require_admin)],
)

# Client-only viewer endpoint
client_router = APIRouter(
    prefix="/api/viewer",
    tags=["Remote viewer"],
)


def _get_application(db: Session, app_id: int) -> Application:
    app = db.get(Application, app_id)
    if not app:
        raise HTTPException(404, "Application not found")
    return app


def _allowed_aliases() -> set[str]:
    aliases = {
        item.strip()
        for item in settings.rdp_allowed_remote_app_aliases.split(",")
        if item.strip()
    }
    if not aliases:
        raise HTTPException(
            503,
            "No approved RemoteApp aliases are configured",
        )
    return aliases


@router.get(
    "/{app_id}/rdp-credentials",
    response_model=RdpCredentialOut,
)
def get_rdp_credentials(
    app_id: int,
    db: Session = Depends(get_db),
):
    _get_application(db, app_id)

    credential = db.scalar(
        select(RdpCredential).where(
            RdpCredential.application_id == app_id
        )
    )

    if not credential:
        raise HTTPException(
            404,
            "RDP credentials not configured",
        )

    return credential


@router.put(
    "/{app_id}/rdp-credentials",
    response_model=RdpCredentialOut,
)
def save_rdp_credentials(
    app_id: int,
    body: RdpCredentialCreate,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    _get_application(db, app_id)

    try:
        from ..services.rdp import build_rdp_connection

        build_rdp_connection(
            hostname=body.hostname,
            username=body.username,
            password=body.password,
            remote_app_alias=body.remote_app_alias,
            allowed_aliases=_allowed_aliases(),
            connection_name=f"APP-{app_id}",
            port=body.port,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc))

    credential = db.scalar(
        select(RdpCredential).where(
            RdpCredential.application_id == app_id
        )
    )

    if credential is None:
        credential = RdpCredential(application_id=app_id)
        db.add(credential)

    credential.hostname = body.hostname.strip()
    credential.port = body.port
    credential.username_encrypted = encrypt_credential(
        body.username
    )
    credential.password_encrypted = encrypt_credential(
        body.password
    )
    credential.remote_app_alias = body.remote_app_alias
    credential.status = "active"

    audit.log(
        db,
        admin.id,
        "rdp_credentials_saved",
        f"application_id={app_id}",
        request,
    )

    try:
        db.commit()
        db.refresh(credential)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            409,
            "RDP credentials could not be saved",
        )

    return credential


@client_router.post(
    "/token",
    response_model=RdpViewerTokenOut,
)
async def create_viewer_token(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_client),
):
    """Issue a Guacamole token only for the client's own running session."""

    # Find the client's assignment from the database.
    assignment = db.scalar(
        select(ClientApplication).where(
            ClientApplication.client_id == user.id
        )
    )

    if not assignment:
        raise HTTPException(
            409,
            "No application is assigned to your account",
        )

    app = _get_application(db, assignment.application_id)

    if app.status != "active":
        raise HTTPException(
            409,
            "Your assigned application is unavailable",
        )

    # A viewer token is only issued after the Agent reports the app running.
    session = session_service.active_session(db, user.id)

    if not session or session.status != "running":
        raise HTTPException(
            409,
            "Your remote application is not running yet",
        )

    if session.application_id != app.id:
        raise HTTPException(
            409,
            "The running session does not match your assigned application",
        )

    credential = db.scalar(
        select(RdpCredential).where(
            RdpCredential.application_id == app.id,
            RdpCredential.status == "active",
        )
    )

    if not credential:
        raise HTTPException(
            503,
            "Remote access credentials are not configured",
        )

    try:
        rdp_username = decrypt_credential(
            credential.username_encrypted
        )
        rdp_password = decrypt_credential(
            credential.password_encrypted
        )

        result = await issue_rdp_token(
            username=f"client-{user.id}",
            connection_name=f"MT-{app.id}",
            hostname=credential.hostname,
            port=credential.port,
            rdp_username=rdp_username,
            rdp_password=rdp_password,
            remote_app_alias=credential.remote_app_alias,
            allowed_aliases=_allowed_aliases(),
        )

    except (RuntimeError, ValueError) as exc:
        # Never return decrypted credentials or internal error details.
        raise HTTPException(
            503,
            "Unable to create the remote viewer connection",
        ) from exc

    audit.log(
        db,
        user.id,
        "viewer_token_issued",
        f"session={session.session_id} application_id={app.id}",
        request,
    )
    db.commit()

    return result
