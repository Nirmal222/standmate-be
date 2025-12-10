from pydantic import BaseModel, EmailStr, Field

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: str | None = None

class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str = Field(min_length=8, max_length=72)

class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(max_length=72)

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
