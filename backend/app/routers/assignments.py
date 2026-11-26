"""Client <-> application assignment. Admin manages; a client may read only their own."""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..deps import get_current_user, require_admin
from ..models import Application, ClientApplication, User
from ..schemas import AssignmentCreate, AssignmentOut, AssignmentUpdate
from ..services import audit, sessions as sess
router = APIRouter(prefix="/api/assignments", tags=["assignments"])


def _client(db: Session, client_id: int) -> User:
    u = db.scalar(select(User).where(User.id == client_id, User.role == "client"))
    if not u:
        raise HTTPException(404, "Client not found")
    return u


def _check_app_free(db: Session, application_id: int, ignore_client: int | None = None) -> Application:
    app = db.get(Application, application_id)
    if not app:
        raise HTTPException(404, "Application not found")
    if app.status != "active":
        raise HTTPException(409, "Application is not active")
    taken = db.scalar(select(ClientApplication).where(ClientApplication.application_id == application_id))
    if taken and taken.client_id != ignore_client:
        raise HTTPException(409, "Application is already assigned to another client")
    return app


def _load(db: Session, client_id: int) -> ClientApplication | None:
    return db.scalar(select(ClientApplication).where(ClientApplication.client_id == client_id)
                     .options(selectinload(ClientApplication.application)))


@router.post("", response_model=AssignmentOut, status_code=201)
def create_assignment(body: AssignmentCreate, request: Request, db: Session = Depends(get_db),
                      admin: User = Depends(require_admin)):
    _client(db, body.client_id)
    if _load(db, body.client_id):
        raise HTTPException(409, "Client already has an assignment; use PUT to change it")
    _check_app_free(db, body.application_id)
    db.add(ClientApplication(client_id=body.client_id, application_id=body.application_id, assigned_by=admin.id))
    audit.log(db, admin.id, "assignment_created", f"client_id={body.client_id} application_id={body.application_id}", request)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Assignment conflict")
    return _load(db, body.client_id)


@router.get("", response_model=list[AssignmentOut])
def list_assignments(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return db.scalars(select(ClientApplication).options(selectinload(ClientApplication.application))
                      .order_by(ClientApplication.id)).all()


@router.get("/{client_id}", response_model=AssignmentOut)
def get_assignment(client_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role != "admin" and user.id != client_id:
        raise HTTPException(403, "Not allowed")       # a client can never see another client's assignment
    a = _load(db, client_id)
    if not a:
        raise HTTPException(404, "No application assigned")
    return a


@router.put("/{client_id}", response_model=AssignmentOut)
def change_assignment(client_id: int, body: AssignmentUpdate, request: Request, db: Session = Depends(get_db),
                      admin: User = Depends(require_admin)):
    _client(db, client_id)
    a = _load(db, client_id)
    if not a:
        raise HTTPException(404, "No application assigned; use POST to create one")
    _check_app_free(db, body.application_id, ignore_client=client_id)
    old = a.application_id
    sess.request_stop_for_client(db, client_id, "Assignment changed")
    a.application_id, a.assigned_by = body.application_id, admin.id
    audit.log(db, admin.id, "assignment_changed", f"client_id={client_id} {old}->{body.application_id}", request)
    db.commit()
    return _load(db, client_id)


@router.delete("/{client_id}", status_code=204)
def remove_assignment(client_id: int, request: Request, db: Session = Depends(get_db),
                      admin: User = Depends(require_admin)):
    a = _load(db, client_id)
    if not a:
        raise HTTPException(404, "No application assigned")
    audit.log(db, admin.id, "assignment_removed", f"client_id={client_id} application_id={a.application_id}", request)
    sess.request_stop_for_client(db, client_id, "Assignment removed")
    db.delete(a)
    db.commit()
