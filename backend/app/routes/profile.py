from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError

from ..database import get_db
from ..models import Session
from ..security import check_password, current_user, hash_password, user_view
from ..storage import remove_user_files
from .auth import issue_action

router = APIRouter(prefix="/profile", tags=["Profile"])


class ProfileUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    current_password: str


class PasswordUpdate(BaseModel):
    current_password: str
    password: str


class DeleteAccount(BaseModel):
    current_password: str


def require_password(user, password):
    if not check_password(password, user.password_hash):
        raise HTTPException(400, "Current password is incorrect.")


@router.patch("")
def update(
    body: ProfileUpdate,
    tasks: BackgroundTasks,
    user=Depends(current_user),
    db=Depends(get_db),
):
    require_password(user, body.current_password)
    if not body.name.strip():
        raise HTTPException(400, "Name cannot be blank.")
    changed_email = user.email != str(body.email).lower()
    user.name, user.email = body.name.strip(), str(body.email).lower()
    if changed_email:
        user.verified = False
        db.execute(delete(Session).where(Session.user_id == user.id))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, "This email is already registered.")
    if changed_email:
        issue_action(db, user, "verify", tasks)
    return {
        "user": user_view(user),
        "message": "Verify your new email before signing in."
        if changed_email
        else "Profile updated.",
    }


@router.post("/password")
def password(body: PasswordUpdate, user=Depends(current_user), db=Depends(get_db)):
    require_password(user, body.current_password)
    user.password_hash = hash_password(body.password)
    db.execute(delete(Session).where(Session.user_id == user.id))
    db.commit()
    return {"message": "Password changed. Sign in again."}


@router.delete("")
def remove(body: DeleteAccount, user=Depends(current_user), db=Depends(get_db)):
    require_password(user, body.current_password)
    if user.role == "admin":
        raise HTTPException(400, "Administrator accounts must be managed by another administrator.")
    remove_user_files(db, user.id)
    db.delete(user)
    db.commit()
    return {"message": "Account and conversion history deleted."}
