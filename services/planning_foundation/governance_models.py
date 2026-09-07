from enum import StrEnum
from typing import Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator

class StrictModel(BaseModel): model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
class Category(StrEnum):
    LOCATION_VENUE='LOCATION_VENUE'; PUBLIC_SPACE_PERMISSION='PUBLIC_SPACE_PERMISSION'; SAFETY_EMERGENCY='SAFETY_EMERGENCY'; TRAFFIC_ACCESS='TRAFFIC_ACCESS'; CROWD_CAPACITY='CROWD_CAPACITY'; FOOD_VENDOR='FOOD_VENDOR'; MINORS_SUPERVISION='MINORS_SUPERVISION'; ANIMALS='ANIMALS'; EQUIPMENT_TEMPORARY_STRUCTURE='EQUIPMENT_TEMPORARY_STRUCTURE'; SOUND_NOISE='SOUND_NOISE'; SPONSOR_COMMERCIAL='SPONSOR_COMMERCIAL'; OTHER='OTHER'
class KnowledgeType(StrEnum): VERIFIED_REQUIREMENT='VERIFIED_REQUIREMENT'; COMMON_PRACTICE='COMMON_PRACTICE'; AI_RISK_ADVISORY='AI_RISK_ADVISORY'; UNKNOWN='UNKNOWN'
class ItemStatus(StrEnum): NEEDS_INFORMATION='NEEDS_INFORMATION'; EVIDENCE_REQUESTED='EVIDENCE_REQUESTED'; PROVIDED='PROVIDED'; SUBMITTED='SUBMITTED'; UNDER_REVIEW='UNDER_REVIEW'; CLEARED='CLEARED'; NOT_APPLICABLE='NOT_APPLICABLE'
class GovernanceItemProposal(StrictModel):
    category:Category; label:str=Field(min_length=1,max_length=200); knowledge_type:KnowledgeType; reason:str|None=None; suggested_documents:list[str]=Field(default_factory=list); status:ItemStatus=ItemStatus.NEEDS_INFORMATION
class GovernanceProposal(StrictModel):
    event_id:UUID; base_event_version:int=Field(ge=1); governance_required:bool; completeness:str; internal_risk:str; review_mode:str; organizer_visible_status:str; location_context:str|None=None; reasoning_summary:str=Field(min_length=1); items:list[GovernanceItemProposal]=Field(default_factory=list)
    @model_validator(mode='after')
    def consistent(self):
        allowed={'NOT_REQUIRED','COMPLETE','INCOMPLETE'}; risks={'LOW','MEDIUM','HIGH'}; modes={'NONE','ORGANIZER','HATCOMMWAYS'}; visible={'NOT_REQUIRED','NEEDS_INFORMATION','EVIDENCE_REQUESTED','SUBMITTED','UNDER_REVIEW','CLEARED'}
        if self.completeness not in allowed or self.internal_risk not in risks or self.review_mode not in modes or self.organizer_visible_status not in visible: raise ValueError('invalid governance classification')
        if not self.governance_required and (self.items or self.completeness!='NOT_REQUIRED'): raise ValueError('not-required governance cannot contain items')
        return self
class ManualItem(StrictModel): category:Category; label:str=Field(min_length=1,max_length=200); reason:str|None=None; authority:str|None=None; evidence_reference:str|None=None; idempotency_key:str=Field(min_length=1,max_length=200)
class ItemPatch(StrictModel): expected_assessment_version:int=Field(ge=1); organizer_note:str|None=None; status:ItemStatus; not_applicable_reason:str|None=None
class EvidenceCreate(StrictModel):
    evidence_type:str
    label:str=Field(min_length=1,max_length=200)
    value_or_reference:str=Field(min_length=1)
    note:str|None=Field(default=None,max_length=2000)
    idempotency_key:str=Field(min_length=1,max_length=200)
    @model_validator(mode='after')
    def valid_non_file_type(self):
        if self.evidence_type not in {'URL','REFERENCE_NUMBER','TEXT_CONFIRMATION'}:
            raise ValueError('invalid non-file evidence type')
        return self
class SubmitGovernance(StrictModel): expected_version:int=Field(ge=1); idempotency_key:str=Field(min_length=1,max_length=200)
