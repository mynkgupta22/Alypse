from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from google.oauth2 import id_token
from google.auth.transport import requests as grequests

from app.core.database import get_db
from app.services.user_service import UserService
from app.schemas.user_schemas import (
    UserCreate, UserResponse,UserUpdate,
    UserLogin, TokenResponse,
    GoogleAuthRequest
)

router = APIRouter(prefix="/users", tags=["Users"])


# -------------------- User CRUD --------------------
@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    service = UserService(db)
    return await service.create_user(user_in)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    service = UserService(db)
    user = await service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/", response_model=List[UserResponse])
async def list_users(db: AsyncSession = Depends(get_db)):
    service = UserService(db)
    return await service.get_all_users()


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, user_in: UserUpdate, db: AsyncSession = Depends(get_db)):
    service = UserService(db)
    user = await service.update_user(user_id, user_in)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    service = UserService(db)
    deleted = await service.delete_user(user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"}


# -------------------- Manual Auth --------------------
@router.post("/login", response_model=TokenResponse)
async def login(user_in: UserLogin, response: Response, db: AsyncSession = Depends(get_db)):
    service = UserService(db)
    session_token = await service.login(user_in.email, user_in.password)
    if not session_token:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        samesite="lax",
        secure=False  # change to True in production with HTTPS
    )
    return {"session_token": session_token}


@router.post("/logout")
async def logout(request: Request, db: AsyncSession = Depends(get_db)):
    service = UserService(db)
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=400, detail="No active session")

    logged_out = await service.logout(session_token)
    if not logged_out:
        raise HTTPException(status_code=404, detail="Session not found")

    response = Response(content="Logged out successfully")
    response.delete_cookie("session_token")
    return response


# -------------------- Google OAuth --------------------
@router.post("/google/login", response_model=TokenResponse)
async def google_login(payload: GoogleAuthRequest, response: Response, db: AsyncSession = Depends(get_db)):
    try:
        # Verify Google ID Token
        idinfo = id_token.verify_oauth2_token(
            payload.id_token,
            grequests.Request(),
            payload.client_id  # must match frontend’s OAuth client ID
        )

        email = idinfo.get("email")
        name = idinfo.get("name", "Unknown")

        if not email:
            raise HTTPException(status_code=400, detail="Invalid Google token")

        service = UserService(db)
        # Auto signup if user does not exist
        user = await service.get_user_by_email(email)
        if not user:
            user_in = UserCreate(email=email, name=name, password="google-oauth")
            user = await service.create_user(user_in)

        # Create session token
        session_token = await service.create_session(user.id)

        # Set HttpOnly cookie
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            samesite="lax",
            secure=False  # set True in production
        )
        return {"session_token": session_token}

    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Google token")


@router.post("/google/logout")
async def google_logout(request: Request, db: AsyncSession = Depends(get_db)):
    service = UserService(db)
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=400, detail="No active session")

    logged_out = await service.logout(session_token)
    if not logged_out:
        raise HTTPException(status_code=404, detail="Session not found")

    response = Response(content="Logged out successfully (Google)")
    response.delete_cookie("session_token")
    return response
