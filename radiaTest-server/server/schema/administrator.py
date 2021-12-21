from pydantic import BaseModel, validator


class LoginSchema(BaseModel):
    account: str
    password: str

    @validator('account')
    def v_account(cls, v):
        if len(v) < 5 or len(v) > 30:
            raise ValueError('5 <= account length <= 30')
        return v

    @validator('password')
    def v_password(cls, v):
        if len(v) < 8:
            raise ValueError('password length >= 8')
        return v


class RegisterSchema(LoginSchema):
    password2: str

    @validator('password2')
    def v_password(cls, v):
        if len(v) < 8:
            raise ValueError('password2 length >= 8')
        return v
