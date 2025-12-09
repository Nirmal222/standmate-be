from pydantic import BaseModel, EmailStr

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: str | None = None

class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class GoogleLogin(BaseModel):
    token: str

class AccessCodeVerify(BaseModel):
    code: str

class AccessCodeCreate(BaseModel):
    email: EmailStr
    code: str | None = None

class AccessCodeResponse(BaseModel):
    code: str
    message: str
