"""Privacy-safe typed map read-model contracts."""
from __future__ import annotations
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID
from pydantic import BaseModel,ConfigDict,Field

class MapEntityType(StrEnum):
    EVENT='EVENT';ACTOR='ACTOR';RESOURCE='RESOURCE';SPONSOR='SPONSOR';SUPPORT_PARTNER='SUPPORT_PARTNER';ACCESS_POINT='ACCESS_POINT';PARKING='PARKING';MEETING_POINT='MEETING_POINT';TRANSPORT='TRANSPORT';OTHER='OTHER'
class LocationPrecision(StrEnum):
    EXACT='EXACT';APPROXIMATE='APPROXIMATE';ZONE='ZONE';DEMO_APPROXIMATE='DEMO_APPROXIMATE'
class MapMarker(BaseModel):
    model_config=ConfigDict(extra='forbid')
    id:UUID;event_id:UUID;entity_type:MapEntityType;entity_id:UUID|None=None;display_name:str
    latitude:float=Field(ge=-90,le=90);longitude:float=Field(ge=-180,le=180)
    area_label:str|None=None;location_precision:LocationPrecision;role:str|None=None;organization:str|None=None;profession:str|None=None
    resource_type:str|None=None;status:str|None=None;visible:bool;metadata:dict[str,Any]=Field(default_factory=dict);created_at:datetime;updated_at:datetime
class MapEvent(BaseModel):
    id:UUID;name:str;location_description:str;starts_at:datetime;ends_at:datetime;timezone:str
class MapReadModel(BaseModel):
    event:MapEvent;markers:list[MapMarker];available_filters:dict[str,list[str]];map_settings:dict[str,Any]
