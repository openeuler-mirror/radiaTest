from typing import List, Optional

from flask import current_app
from pydantic import BaseModel, root_validator, validator

from server.schema import AttachmentType, RequirementPublishType, Operator, LoggingType
from server.schema.base import PageBaseSchema


class RequirementQuerySchema(PageBaseSchema):
    status: Optional[str]
    title: Optional[str]
    remark: Optional[str]
    description: Optional[str]
    payload: Optional[float]
    payload_operator: Optional[Operator]
    period: Optional[int]
    period_operator: Optional[Operator]
    influence_require: Optional[int]
    behavior_require: Optional[int]
    total_reward: Optional[int]


class RequirmentCreateSchema(BaseModel):
    title: str
    remark: str
    description: str
    payload: float
    period: int
    influence_require: int
    behavior_require: int
    total_reward: int
    packages: List[dict] = []
    milestones: List[int] = []

    @validator("behavior_require")
    def validate_behavior_range(cls, v):
        if v < 0 or v > 100:
            raise ValueError("behavior should be in range 0 to 100")
        return v

    @root_validator
    def validate_positive(cls, values):
        value_list = [
            "payload", 
            "period", 
            "influence_require", 
            "behavior_require", 
            "total_reward"
        ]
        for key in value_list:
            if values.get(key) < 0:
                raise ValueError(
                    f"the {key} of requirement shoule not be less than zero"
                )

        if len(values.get("packages")) > 0:
            for package in values.get("packages"):
                if not isinstance(package.get("name"), str):
                    raise ValueError(
                        "the name of package should not be empty"
                    )
                if not isinstance(package.get("targets"), list) or len(package.get("targets")) == 0:
                    raise ValueError(
                        "the targets of package of requriement should not be empty"
                    )
                for target in package.get("targets"):
                    if target not in current_app.config.get("REQUIREMENT_PACKAGE_TARGETS"):
                        raise ValueError(
                            f"the target {target} not valid"
                        )
        
        return values


class AttachmentBaseSchema(BaseModel):
    type: AttachmentType
    

class AttachmentFilenameSchema(AttachmentBaseSchema):
    filename: str


class AttachmentLockSchema(AttachmentBaseSchema):
    locked: bool


class ProgressFeedbackSchema(BaseModel):
    type: LoggingType
    percentage: Optional[int] 
    content: str

    @validator('percentage')
    def validate_type(cls, v):
        if v < 0 or v > 100:
            raise ValueError("percentage must be between 0 and 100")
        return v


class PackageCompletionSchema(BaseModel):
    completions: List[str]

    @validator('completions')
    def validate_completions(cls, v):
        for item in v:
            if item not in current_app.config.get("REQUIREMENT_PACKAGE_TARGETS"):
                raise ValueError(f"{item} not in valid requirement package targets")
        return v


class PackageTaskCreateSchema(BaseModel):
    executor_id: str


class UserRewardSchema(BaseModel):
    user_id: str
    user_name: str
    reward: int


class RequirementItemRewardDivideSchema(BaseModel):
    strategies: List[UserRewardSchema]