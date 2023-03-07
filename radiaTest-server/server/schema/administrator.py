from pydantic import BaseModel, validator, root_validator


class LoginSchema(BaseModel):
    account: str
    password: str


class RegisterSchema(LoginSchema):
    password2: str

    @validator('password2')
    def v_password(cls, v):
        if len(v) < 8:
            raise ValueError('password2 length >= 8')
        return v


class ChangePasswdSchema(BaseModel):
    account: str
    old_password: str
    new_password: str
    re_new_password: str

    @validator('account')
    def v_account(cls, v):
        if len(v) < 5 or len(v) > 30:
            raise ValueError('account length should be greater than 5 and less than 30')
        return v

    @root_validator
    def v_password(cls, values):
        if len(values['old_password']) < 8 or len(values['new_password']) < 8 or len(values['re_new_password']) < 8:
            raise ValueError('password length should be greater than 8')

        if values['new_password'] != values['re_new_password']:
            raise ValueError('The passwords entered twice are different')
        return values
