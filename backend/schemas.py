from pydantic import BaseModel

class PreValidationCreate(BaseModel):
    employee_id: int
    action_type: str
    comments: str | None = None

class PreValidationResponse(BaseModel):
    id: int
    employee_id: int
    action_type: str
    status: str
    comments: str | None

    class Config:
        orm_mode = True

class DP2001Create(BaseModel):
    employee_id: int
    prevalidation_id: int
    action_type: str
    comments: str | None = None

class DP2001Response(BaseModel):
    id: int
    employee_id: int
    prevalidation_id: int
    action_type: str
    status: str
    comments: str | None

    class Config:
        orm_mode = True
