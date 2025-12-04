from typing import Annotated
from datetime import timedelta
import httpx
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt

from core.database import get_db
from core import security
from core.config import settings
from models.user import User
from schemas.auth import Token, UserCreate, UserLogin
from api import deps

router = APIRouter()

# OAuth Configuration
GOOGLE_AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"
REDIRECT_URI = f"{settings.BACKEND_URL}/api/v1/auth/callback"

@router.post("/signup", response_model=Token)
async def signup(
    user_in: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    # Check if user exists
    result = await db.execute(select(User).where(User.email == user_in.email))
    user = result.scalars().first()
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
        
    # Check username
    result = await db.execute(select(User).where(User.username == user_in.username))
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )

    # Create new user
    db_user = User(
        email=user_in.email,
        username=user_in.username,
        hashed_password=security.get_password_hash(user_in.password),
        auth_provider="email"
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)

    # Generate token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        subject=db_user.email, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    # Authenticate user
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()
    
    if not user or not user.hashed_password or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        subject=user.email, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/google-login")
def google_login():
    return RedirectResponse(
        url=f"{GOOGLE_AUTH_URI}"
            f"?client_id={settings.GOOGLE_CLIENT_ID}"
            f"&redirect_uri={REDIRECT_URI}"
            f"&response_type=code"
            f"&scope=openid%20email%20profile"
    )

@router.get("/callback")
async def callback(request: Request, db: Annotated[AsyncSession, Depends(get_db)]):
    code = request.query_params.get("code")
    if not code:
        return RedirectResponse(url=f"{settings.FRONTEND_BASE_URL}/signup?error=missing_code")

    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            GOOGLE_TOKEN_URI,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": REDIRECT_URI,
                "grant_type": "authorization_code",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        token_data = token_res.json()

        if "id_token" not in token_data:
            return RedirectResponse(url=f"{settings.FRONTEND_BASE_URL}/signup?error=oauth_failed")

        id_token = token_data["id_token"]
        # In a real scenario, you should verify the signature of id_token
        # Here we decode unverified claims assuming direct communication with Google's token endpoint is secure enough for this step
        # or use library to verify. The reference code used get_unverified_claims.
        userinfo = jwt.get_unverified_claims(id_token)
        print(userinfo, "<-- user information parsed")
        email = userinfo.get("email")
        if not email:
             return RedirectResponse(url=f"{settings.FRONTEND_BASE_URL}/signup?error=no_email")

        # Find or Create User
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalars().first()
        
        if not user:
            # Infer username
            base_username = email.split("@")[0]
            # Check username existence
            result = await db.execute(select(User).where(User.username == base_username))
            if result.scalars().first():
                 import uuid
                 base_username = f"{base_username}_{uuid.uuid4().hex[:4]}"
                 
            user = User(
                email=email,
                username=base_username,
                hashed_password=None,
                auth_provider="google",
                is_active=True
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            
        # Create our JWT
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = security.create_access_token(
            subject=user.email, expires_delta=access_token_expires
        )
        
        # Redirect to Frontend with token
        return RedirectResponse(
            url=f"{settings.FRONTEND_BASE_URL}/auth/success/{access_token}"
        )

@router.get("/me")
async def read_users_me(
    current_user: Annotated[User, Depends(deps.get_current_user)]
):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "auth_provider": current_user.auth_provider
    }
