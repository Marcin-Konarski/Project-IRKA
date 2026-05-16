from pydantic import BaseModel


class TelegramCodeRequest(BaseModel):
    phone: str


class TelegramCodeVerify(BaseModel):
    phone: str
    code: str
    phone_code_hash: str


class TelegramCodeResponse(BaseModel):
    phone_code_hash: str
    message: str
