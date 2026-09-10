from __future__ import annotations
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID
from pydantic import BaseModel,ConfigDict,Field,model_validator

class ReplanChangeType(StrEnum):
    WORK_START_CHANGE='WORK_START_CHANGE'; WORK_END_CHANGE='WORK_END_CHANGE'; WORK_WINDOW_SHIFT='WORK_WINDOW_SHIFT'
    STAGE_TIMING_CHANGE='STAGE_TIMING_CHANGE'; DEPENDENCY_TIMING_ADJUSTMENT='DEPENDENCY_TIMING_ADJUSTMENT'
    MEETING_RESCHEDULE='MEETING_RESCHEDULE'; ACTOR_REASSIGNMENT_SUGGESTION='ACTOR_REASSIGNMENT_SUGGESTION'
    REMOVE_WORK_FROM_CURRENT_WINDOW='REMOVE_WORK_FROM_CURRENT_WINDOW'; SPLIT_WORK_SUGGESTION='SPLIT_WORK_SUGGESTION'; OTHER='OTHER'

class ReplanChange(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    change_type:ReplanChangeType
    target_work_id:UUID|None=None; target_stage_id:UUID|None=None; target_meeting_id:UUID|None=None; target_actor_id:UUID|None=None
    proposed_start:datetime|None=None; proposed_end:datetime|None=None
    concise_reason:str=Field(min_length=1,max_length=500)
    requires_human_approval:bool=True
    @model_validator(mode='after')
    def window(self):
        if (self.proposed_start is None)!=(self.proposed_end is None): raise ValueError('proposed start and end must be provided together')
        if self.proposed_start and self.proposed_end<=self.proposed_start: raise ValueError('proposed end must be after start')
        return self

class ReplanDecision(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    event_id:UUID; blocker_id:UUID; affected_work_resolution_id:UUID; coordination_proposal_id:UUID
    current_plan_version:int=Field(ge=1); source_graph_fingerprint:str=Field(pattern=r'^[0-9a-f]{64}$')
    proposed_changes:list[ReplanChange]=Field(min_length=1,max_length=30)
    rationale:str=Field(min_length=1,max_length=3000); confidence:float=Field(ge=0,le=1)

class ReplanProposalSnapshot(ReplanDecision):
    id:UUID; request_id:UUID; unaffected_work_ids:list[UUID]; affected_actor_ids:list[UUID]
    status:str; source_fingerprint:str; source_versions:dict[str,Any]
    provider_name:str; model_id:str; agent_name:str; agent_version:str; stop_reason:str; usage:dict[str,int]; created_at:datetime; decided_at:datetime|None=None

class ReplanRequest(BaseModel):
    model_config=ConfigDict(extra='forbid'); retry:bool=False

class ReplanContext(BaseModel):
    model_config=ConfigDict(extra='forbid')
    event:dict[str,Any]; blocker:dict[str,Any]; assessment:dict[str,Any]; resolution:dict[str,Any]; coordination:dict[str,Any]
    affected_stages:list[dict[str,Any]]=[]; affected_work:list[dict[str,Any]]=[]; affected_actors:list[dict[str,Any]]=[]; relevant_meetings:list[dict[str,Any]]=[]
    unaffected_work_ids:list[UUID]=[]; source_fingerprint:str; source_versions:dict[str,Any]

class ReplanDecisionRequest(BaseModel):
    model_config=ConfigDict(extra='forbid'); expected_event_version:int=Field(ge=1)
