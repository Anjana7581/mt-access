"""Admin-only MetaTrader installation registry. Every path goes through path_policy."""
from pathlib import PureWindowsPath
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_admin
from ..models import Application, User
from ..schemas import ApplicationCreate, ApplicationOut, ApplicationUpdate
from ..services import audit, sessions as sess
from ..services.path_policy import PathPolicyError, validate_app_paths

router = APIRouter(prefix="/api/applications", tags=["applications"], dependencies=[Depends(require_admin)])


def _validated(app_type, exe, wd):
    try:
        return validate_app_paths(app_type, exe, wd)
    except PathPolicyError as e:
        raise HTTPException(422, str(e))


def _get(db: Session, app_id: int) -> Application:
    app = db.get(Application, app_id)
    if not app:
        raise HTTPException(404, "Application not found")
    return app

def _changes_launch_target(app: Application, ch: dict) -> bool:
    """True if the request would alter the type, executable or working directory. Paths are compared the
    Windows way (case- and slash-insensitive), so re-sending the same path is not a change."""
    if ch.get("application_type") not in (None, app.application_type):
        return True
    for field in ("executable_path", "working_directory"):
        new = (ch.get(field) or "").strip()
        if new and PureWindowsPath(new) != PureWindowsPath(getattr(app, field)):
            return True
    return False

@router.post("", response_model=ApplicationOut, status_code=201)
def create_application(body: ApplicationCreate, request: Request, db: Session = Depends(get_db),
                       admin: User = Depends(require_admin)):
    exe, wd = _validated(body.application_type, body.executable_path, body.working_directory)
    if db.scalar(select(Application.id).where(func.lower(Application.executable_path) == exe.lower())):
        raise HTTPException(409, "An application with this executable path already exists")
    app = Application(application_name=body.application_name.strip(), application_type=body.application_type,
                      executable_path=exe, working_directory=wd, status=body.status)
    db.add(app)
    try:
        db.flush()
        audit.log(db, admin.id, "application_created", f"application_id={app.id} path={exe}", request)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "An application with this executable path already exists")
    return app


@router.get("", response_model=list[ApplicationOut])
def list_applications(db: Session = Depends(get_db)):
    return db.scalars(select(Application).order_by(Application.id)).all()


@router.get("/{app_id}", response_model=ApplicationOut)
def get_application(app_id: int, db: Session = Depends(get_db)):
    return _get(db, app_id)


@router.put("/{app_id}", response_model=ApplicationOut)
def update_application(app_id: int, body: ApplicationUpdate, request: Request, db: Session = Depends(get_db),
                       admin: User = Depends(require_admin)):
    app = _get(db, app_id)
    ch = body.model_dump(exclude_unset=True)
        # Checked before ANY field is touched: changing what a live session runs would leave the already-running
    # process unmanaged (the agent finds it by the registered path). The admin must disconnect the client first.
    if _changes_launch_target(app, ch) and sess.has_active_session_for_application(db, app.id):
        raise HTTPException(409, "Application has an active session; disconnect the client before changing its type or path")
    app_type = ch.get("application_type", app.application_type)
    exe_in = ch.get("executable_path", app.executable_path)
    # If the path changes and no working dir was given, derive it; otherwise re-check the supplied/existing one.
    wd_in = ch.get("working_directory") if "executable_path" in ch or "working_directory" in ch else app.working_directory
    exe, wd = _validated(app_type, exe_in, wd_in)
    clash = db.scalar(select(Application.id).where(func.lower(Application.executable_path) == exe.lower(), Application.id != app.id))
    if clash:
        raise HTTPException(409, "Another application already uses this executable path")
    app.application_type, app.executable_path, app.working_directory = app_type, exe, wd
    if ch.get("application_name"):
        app.application_name = ch["application_name"].strip()
    if ch.get("status"):
        app.status = ch["status"]
        if app.status == "inactive":
            sess.request_stop_for_application(db, app.id, "Application deactivated")
    audit.log(db, admin.id, "application_updated", f"application_id={app.id} fields={sorted(ch)}", request)
    db.commit()
    return app


@router.delete("/{app_id}", status_code=204)
def delete_application(app_id: int, request: Request, db: Session = Depends(get_db),
                       admin: User = Depends(require_admin)):
    app = _get(db, app_id)
    if app.assignment:
        raise HTTPException(409, "Application is assigned to a client; unassign it first")
    audit.log(db, admin.id, "application_deleted", f"application_id={app.id}", request)
    db.delete(app)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Application has session history; set it inactive instead")
