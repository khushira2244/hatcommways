from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel,ConfigDict,Field,model_validator

class StrictModel(BaseModel): model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
class ParticipationSelection(StrictModel):
    actor_requirement_id:UUID
    preference:Literal['PREFERRED','CAN_ALSO_HELP']='PREFERRED'
class Availability(StrictModel):
    availability_type:Literal['FULL','PARTIAL','FLEXIBLE']
    availability_start:datetime|None=None
    availability_end:datetime|None=None
    max_commitment_minutes:int|None=Field(default=None,gt=0)
    allow_alternative_work:bool=False
    @model_validator(mode='after')
    def valid_window(self):
        if self.availability_type=='PARTIAL' and (not self.availability_start or not self.availability_end): raise ValueError('partial availability requires start and end')
        if self.availability_start and self.availability_end and self.availability_end<=self.availability_start: raise ValueError('availability end must be after start')
        if self.availability_type!='PARTIAL': self.availability_start=self.availability_end=None
        return self
class AdvisoryRequest(StrictModel):
    selections:list[ParticipationSelection]=Field(min_length=1)
    availability:Availability
class AdvisoryFinding(StrictModel):
    level:Literal['INFO','WARNING','CONFLICT']
    message:str=Field(min_length=1,max_length=500)
    affected_selection_ids:list[UUID]=Field(default_factory=list)
class ParticipationAdvisory(StrictModel):
    overall_advisory:Literal['GOOD_FIT','REVIEW_SUGGESTED','CONFLICT']
    findings:list[AdvisoryFinding]=Field(default_factory=list)
    suggested_adjustments:list[str]=Field(default_factory=list)
    explanation:str=Field(min_length=1,max_length=2000)
class ParticipationSubmit(StrictModel):
    advisory_id:UUID
    note:str|None=Field(default=None,max_length=2000)
    idempotency_key:str=Field(min_length=1,max_length=200)
class ParticipationDecisionBody(StrictModel):
    decision:Literal['APPROVE','REJECT']
    idempotency_key:str=Field(min_length=1,max_length=200)
