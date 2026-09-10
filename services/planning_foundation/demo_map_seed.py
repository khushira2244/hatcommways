"""Deterministic synthetic map fixture for local demos and hackathon judging."""
from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from psycopg.types.json import Jsonb

from .database import Database

FIXTURE_VERSION = "hatcommways-map-demo-v1"
DEMO_PASSWORD = "HatcommwaysDemo2026!"
PASSWORD_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$9QWFU6lIQTh1btqPI6bMvg$"
    "PZNILHBr/XE4lAHCMuxwtrsxa69n2SBNlO8HAMmjvk8"
)
CREATED_AT = datetime(2026, 9, 1, 0, 0, tzinfo=timezone.utc)


def stable_id(key: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"{FIXTURE_VERSION}:{key}")


@dataclass(frozen=True)
class Marker:
    key: str
    kind: str
    name: str
    latitude: float
    longitude: float
    area: str
    precision: str = "DEMO_APPROXIMATE"
    actor: str | None = None
    resource_type: str | None = None
    organization: str | None = None
    profession: str | None = None


@dataclass(frozen=True)
class EventFixture:
    key: str
    name: str
    purpose: str
    location: str
    start: datetime
    roles: tuple[str, ...]
    markers: tuple[Marker, ...]


def m(key: str, kind: str, name: str, lat: float, lng: float, area: str, **values):
    return Marker(key,kind,name,lat,lng,area,**values)


EVENTS = (
    EventFixture(
        "ghasi-talab",
        "Ghasi Talab Community Cleanup & Restoration Drive",
        "Synthetic demonstration of volunteer, resource, and access coordination.",
        "Dhumsatoli / Ghasi Talab area, Ranchi — synthetic demo area",
        datetime(2026,10,3,2,30,tzinfo=timezone.utc),
        ("Cleanup Volunteer","Waste Sorting Volunteer","Volunteer Coordinator",
         "Safety / Access Volunteer","Documentation Volunteer","Resource Coordinator",
         "Cleanup Volunteer","Waste Sorting Volunteer"),
        (
            m("event","EVENT","Ghasi Talab cleanup hub",23.3574,85.3150,"Ghasi Talab"),
            m("a1","ACTOR","Demo Volunteer A",23.3578,85.3146,"North Bank",actor="a1",organization="Dhumsatoli Neighbourhood Group",profession="Student"),
            m("a2","ACTOR","Demo Volunteer B",23.3571,85.3143,"North Bank",actor="a2",organization="Independent Volunteer",profession="Shopkeeper"),
            m("a3","ACTOR","Demo Volunteer C",23.3566,85.3151,"Water Edge",actor="a3",organization="Green Ward Collective",profession="Teacher"),
            m("a4","ACTOR","Demo Volunteer D",23.3569,85.3157,"Water Edge",actor="a4",organization="Independent Volunteer",profession="Student"),
            m("a5","ACTOR","Demo Volunteer E",23.3577,85.3158,"East Path",actor="a5",organization="Dhumsatoli Neighbourhood Group",profession="Coordinator"),
            m("a6","ACTOR","Demo Volunteer F",23.3582,85.3153,"East Path",actor="a6",organization="Green Ward Collective",profession="Photographer"),
            m("a7","ACTOR","Demo Volunteer G",23.3565,85.3144,"Sorting Zone",actor="a7",organization="Independent Volunteer",profession="Driver"),
            m("a8","ACTOR","Demo Volunteer H",23.3580,85.3140,"Sorting Zone",actor="a8",organization="Dhumsatoli Neighbourhood Group",profession="Community Worker"),
            m("r1","RESOURCE","Gloves and waste bags",23.3573,85.3142,"Main Entry",resource_type="Cleanup supplies"),
            m("r2","RESOURCE","Drinking water point",23.3579,85.3154,"East Path",resource_type="Water"),
            m("r3","RESOURCE","Waste collection vehicle",23.3563,85.3148,"Pickup Zone",resource_type="Transport"),
            m("r4","RESOURCE","First-aid and equipment point",23.3570,85.3155,"Water Edge",resource_type="Safety"),
            m("s1","SPONSOR","Demo Local Business Sponsor",23.3581,85.3148,"Main Entry",organization="Demo Ranchi Business Circle"),
            m("s2","SUPPORT_PARTNER","Demo Ward Support Desk",23.3576,85.3152,"Main Entry",organization="Demo Community Support Network"),
            m("o1","ACCESS_POINT","Main entry",23.3584,85.3146,"Main Entry"),
            m("o2","ACCESS_POINT","Alternate entry",23.3564,85.3156,"South Path"),
            m("o3","PARKING","Parking and pickup point",23.3561,85.3143,"Pickup Zone"),
        ),
    ),
    EventFixture(
        "tree-plantation",
        "Neighborhood Tree Plantation Drive",
        "Synthetic demonstration of area-based planting and resource coordination.",
        "Community green corridor, Ranchi — synthetic demo area",
        datetime(2026,10,10,2,30,tzinfo=timezone.utc),
        ("Planting Team","Planting Team","Watering Team","Watering Team",
         "Zone Coordinator","Resource Coordinator"),
        (
            m("event","EVENT","Tree plantation coordination hub",23.3690,85.3230,"Central Hub"),
            m("a1","ACTOR","Demo Planter A",23.3695,85.3222,"Planting Zone A",actor="a1",organization="Green Ward Collective",profession="Student",precision="ZONE"),
            m("a2","ACTOR","Demo Planter B",23.3697,85.3225,"Planting Zone A",actor="a2",profession="Gardener",precision="ZONE"),
            m("a3","ACTOR","Demo Watering Volunteer A",23.3684,85.3236,"Planting Zone B",actor="a3",organization="Neighbourhood Youth Circle",precision="ZONE"),
            m("a4","ACTOR","Demo Watering Volunteer B",23.3686,85.3239,"Planting Zone B",actor="a4",profession="Student",precision="ZONE"),
            m("a5","ACTOR","Demo Zone Coordinator",23.3691,85.3232,"Central Hub",actor="a5",organization="Green Ward Collective",profession="Community Worker",precision="ZONE"),
            m("a6","ACTOR","Demo Resource Coordinator",23.3688,85.3228,"Central Hub",actor="a6",profession="Gardener",precision="ZONE"),
            m("r1","RESOURCE","Sapling distribution point",23.3693,85.3234,"Central Hub",resource_type="Saplings"),
            m("r2","RESOURCE","Tool and equipment point",23.3698,85.3229,"Planting Zone A",resource_type="Tools"),
            m("r3","RESOURCE","Water refill point",23.3682,85.3233,"Planting Zone B",resource_type="Water"),
            m("o1","TRANSPORT","Sapling transport drop",23.3700,85.3231,"Transport Edge"),
            m("o2","MEETING_POINT","Planting team briefing point",23.3692,85.3226,"Central Hub"),
            m("o3","ACCESS_POINT","Green corridor entrance",23.3680,85.3238,"Planting Zone B"),
        ),
    ),
    EventFixture(
        "health-awareness",
        "Community Health & Awareness Camp",
        "Synthetic coordination fixture with no participant health information.",
        "Community hall precinct, Ranchi — synthetic demo area",
        datetime(2026,10,17,3,30,tzinfo=timezone.utc),
        ("Registration Volunteer","Registration Volunteer","Crowd Support Volunteer",
         "Logistics Support","Awareness Desk Volunteer"),
        (
            m("event","EVENT","Health awareness camp hub",23.3440,85.3090,"Community Hall"),
            m("a1","ACTOR","Demo Registration Volunteer A",23.3443,85.3086,"Registration Zone",actor="a1",organization="Demo Community Health Collective",profession="Student"),
            m("a2","ACTOR","Demo Registration Volunteer B",23.3441,85.3084,"Registration Zone",actor="a2",organization="Independent Volunteer",profession="Teacher"),
            m("a3","ACTOR","Demo Crowd Support Volunteer",23.3437,85.3094,"Waiting Area",actor="a3",organization="Neighbourhood Support Circle",profession="Community Worker"),
            m("a4","ACTOR","Demo Logistics Volunteer",23.3435,85.3089,"Supply Zone",actor="a4",organization="Demo Logistics Collective",profession="Driver"),
            m("a5","ACTOR","Demo Awareness Desk Volunteer",23.3444,85.3093,"Awareness Area",actor="a5",organization="Demo Community Health Collective",profession="Educator"),
            m("r1","RESOURCE","Registration supplies",23.3442,85.3087,"Registration Zone",resource_type="Stationery"),
            m("r2","RESOURCE","Awareness material point",23.3445,85.3091,"Awareness Area",resource_type="Information materials"),
            m("r3","RESOURCE","Operational medical-support area",23.3438,85.3092,"Support Area",resource_type="Operational support"),
            m("s1","SUPPORT_PARTNER","Demo Community Support Organization",23.3439,85.3087,"Community Hall",organization="Demo Community Support Organization"),
            m("s2","SPONSOR","Demo Awareness Sponsor",23.3446,85.3088,"Awareness Area",organization="Demo Civic Sponsor Network"),
            m("o1","ACCESS_POINT","Camp entry and helpdesk",23.3447,85.3085,"Entry Zone"),
            m("o2","MEETING_POINT","Volunteer briefing corner",23.3436,85.3095,"Waiting Area"),
        ),
    ),
    EventFixture(
        "cultural-festival",
        "Local Cultural & Community Festival",
        "Synthetic demonstration of festival access, stage, vendor, and sponsor coordination.",
        "Community festival grounds, Ranchi — synthetic demo area",
        datetime(2026,10,24,10,30,tzinfo=timezone.utc),
        ("Stage Coordinator","Entry Support Volunteer","Crowd Support Volunteer",
         "Documentation Volunteer","Vendor Support Coordinator"),
        (
            m("event","EVENT","Community festival hub",23.3740,85.3350,"Festival Centre"),
            m("a1","ACTOR","Demo Stage Coordinator",23.3742,85.3353,"Performance Zone",actor="a1",organization="Demo Cultural Collective",profession="Event Coordinator"),
            m("a2","ACTOR","Demo Entry Volunteer",23.3747,85.3344,"Main Gate",actor="a2",organization="Neighbourhood Youth Circle",profession="Student"),
            m("a3","ACTOR","Demo Crowd Volunteer",23.3736,85.3355,"Audience Zone",actor="a3",profession="Community Worker"),
            m("a4","ACTOR","Demo Documentation Volunteer",23.3741,85.3347,"Festival Centre",actor="a4",organization="Demo Cultural Collective",profession="Photographer"),
            m("a5","ACTOR","Demo Vendor Coordinator",23.3735,85.3345,"Vendor Zone",actor="a5",organization="Demo Vendor Association",profession="Shopkeeper"),
            m("r1","RESOURCE","Stage equipment point",23.3743,85.3355,"Performance Zone",resource_type="Stage equipment"),
            m("r2","RESOURCE","Vendor support desk",23.3734,85.3347,"Vendor Zone",resource_type="Vendor supplies"),
            m("r3","RESOURCE","Community water point",23.3738,85.3352,"Audience Zone",resource_type="Water"),
            m("s1","SPONSOR","Demo Festival Sponsor",23.3744,85.3348,"Festival Centre",organization="Demo Local Arts Sponsor"),
            m("s2","SUPPORT_PARTNER","Demo Cultural Support Partner",23.3737,85.3349,"Festival Centre",organization="Demo Cultural Support Network"),
            m("o1","ACCESS_POINT","Festival main entry",23.3748,85.3345,"Main Gate"),
            m("o2","ACCESS_POINT","Festival alternate entry",23.3732,85.3354,"Alternate Gate"),
            m("o3","PARKING","Festival transport and parking",23.3730,85.3342,"Transport Zone"),
        ),
    ),
)


def _account(connection, key: str, name: str, account_type: str = "INDIVIDUAL") -> UUID:
    account_id=stable_id(f"account:{key}")
    connection.execute(
        """INSERT INTO accounts(id,email,display_name,account_type,status,password_hash,
                                created_at,updated_at)
           VALUES(%s,%s,%s,%s,'ACTIVE',%s,%s,%s)
           ON CONFLICT(id) DO UPDATE SET display_name=excluded.display_name,
             account_type=excluded.account_type,status='ACTIVE',updated_at=excluded.updated_at""",
        (account_id,f"{key}@demo.hatcommways.invalid",name,account_type,
         PASSWORD_HASH,CREATED_AT,CREATED_AT),
    )
    return account_id


def _proposal(connection, event_id: UUID, key: str, organizer_id: UUID) -> UUID:
    proposal_id=stable_id(f"{key}:proposal")
    connection.execute(
        """INSERT INTO proposals(id,proposal_type,target_type,target_id,created_by,
           base_versions,payload,status,idempotency_key,correlation_id,created_at,decided_at)
           VALUES(%s,'DEMO_FIXTURE','EVENT',%s,'fixture:demo-map',%s,%s,'APPROVED',
                  %s,%s,%s,%s)
           ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,status='APPROVED',
             decided_at=excluded.decided_at""",
        (proposal_id,event_id,Jsonb({"event":1}),
         Jsonb({"synthetic_demo":True,"fixture":FIXTURE_VERSION}),
         f"{FIXTURE_VERSION}:{key}:proposal",stable_id(f"{key}:correlation"),
         CREATED_AT,CREATED_AT),
    )
    return proposal_id


def _seed_event(connection, fixture: EventFixture) -> dict[str, Any]:
    event_id=stable_id(f"{fixture.key}:event")
    organizer_id=_account(connection,f"{fixture.key}.organizer",
                          f"Demo Organizer — {fixture.name}")
    connection.execute(
        """INSERT INTO events(id,organizer_id,name,category,purpose,event_type,starts_at,
             ends_at,timezone,location_description,planning_context,version,created_at,updated_at)
           VALUES(%s,%s,%s,'DEMO',%s,'community_demo',%s,%s,'Asia/Kolkata',%s,%s,1,%s,%s)
           ON CONFLICT(id) DO UPDATE SET name=excluded.name,purpose=excluded.purpose,
             starts_at=excluded.starts_at,ends_at=excluded.ends_at,
             location_description=excluded.location_description,
             planning_context=excluded.planning_context,updated_at=excluded.updated_at""",
        (event_id,organizer_id,fixture.name,fixture.purpose,fixture.start,
         fixture.start+timedelta(hours=6),fixture.location,
         Jsonb({
             "detailed_purpose":fixture.purpose,
             "expected_scale":len([x for x in fixture.markers if x.kind=="ACTOR"]),
             "intended_participants":["Community Members","Volunteers"],
             "known_resources":"Synthetic resources shown in Event Setup and the map.",
             "known_requirements":"All locations are approximate demonstration data.",
             "constraints":"No live GPS, home addresses, or personal records.",
             "desired_outcomes":"Demonstrate privacy-safe community coordination.",
             "organizer_notes":f"Synthetic fixture: {FIXTURE_VERSION}",
             "theme":"Community / Neighbor",
         }),CREATED_AT,CREATED_AT),
    )
    connection.execute(
        """INSERT INTO event_memberships(event_id,account_id,role,status,created_at,updated_at)
           VALUES(%s,%s,'ORGANIZER','ACTIVE',%s,%s)
           ON CONFLICT(event_id,account_id,role) DO UPDATE SET status='ACTIVE',
             updated_at=excluded.updated_at""",
        (event_id,organizer_id,CREATED_AT,CREATED_AT),
    )
    resources=[
        {"name":x.name,"category":x.resource_type}
        for x in fixture.markers if x.kind=="RESOURCE"
    ]
    support=[
        {"name":x.name,"type":x.kind,"visibility_enabled":True}
        for x in fixture.markers if x.kind in {"SPONSOR","SUPPORT_PARTNER"}
    ]
    connection.execute(
        """INSERT INTO event_setups(event_id,sponsors_support,resource_needs,map_enabled,
             default_view,participation_dimensions,event_visibility,show_actor_tree,
             show_sponsors,show_resources,created_at,updated_at)
           VALUES(%s,%s,%s,true,'ALL_MARKERS',%s,'PUBLIC',true,true,true,%s,%s)
           ON CONFLICT(event_id) DO UPDATE SET sponsors_support=excluded.sponsors_support,
             resource_needs=excluded.resource_needs,map_enabled=true,
             default_view=excluded.default_view,
             participation_dimensions=excluded.participation_dimensions,
             event_visibility='PUBLIC',show_actor_tree=true,show_sponsors=true,
             show_resources=true,updated_at=excluded.updated_at""",
        (event_id,Jsonb(support),Jsonb(resources),
         Jsonb(["AREA","ROLE","ORGANIZATION","PROFESSION"]),
         CREATED_AT,CREATED_AT),
    )
    proposal_id=_proposal(connection,event_id,fixture.key,organizer_id)
    stage_id=stable_id(f"{fixture.key}:stage")
    work_id=stable_id(f"{fixture.key}:work")
    connection.execute(
        """INSERT INTO stages(id,event_id,canonical_name,purpose,stage_order,starts_at,
             ends_at,version,source_proposal_id,created_at,updated_at)
           VALUES(%s,%s,'Demo Operations','Coordinate the synthetic demo event',1,
                  %s,%s,1,%s,%s,%s)
           ON CONFLICT(id) DO UPDATE SET canonical_name=excluded.canonical_name,
             starts_at=excluded.starts_at,ends_at=excluded.ends_at,
             updated_at=excluded.updated_at""",
        (stage_id,event_id,fixture.start,fixture.start+timedelta(hours=6),
         proposal_id,CREATED_AT,CREATED_AT),
    )
    connection.execute(
        """INSERT INTO work_items(id,event_id,stage_id,canonical_name,purpose,work_order,
             estimated_person_hours,work_share,starts_at,ends_at,version,
             source_proposal_id,created_at,updated_at)
           VALUES(%s,%s,%s,'Demo Event Operations','Coordinate visible demo work',1,
                  48,100,%s,%s,1,%s,%s,%s)
           ON CONFLICT(id) DO UPDATE SET starts_at=excluded.starts_at,
             ends_at=excluded.ends_at,updated_at=excluded.updated_at""",
        (work_id,event_id,stage_id,fixture.start,fixture.start+timedelta(hours=6),
         proposal_id,CREATED_AT,CREATED_AT),
    )
    role_ids={}
    for index,role in enumerate(dict.fromkeys(fixture.roles),1):
        role_id=stable_id(f"{fixture.key}:role:{role}")
        role_ids[role]=role_id
        connection.execute(
            """INSERT INTO actor_requirements(id,event_id,stage_id,work_id,role_category,
                 canonical_role_name,responsibility_summary,minimum_required_count,
                 relevant_capabilities,rough_effort_expectation,rationale,version,
                 source_proposal_id,created_at,updated_at)
               VALUES(%s,%s,%s,%s,'DEMO_ROLE',%s,'Synthetic demo assignment',1,%s,
                      'One demo shift','Required for the demo coordination pattern',1,%s,%s,%s)
               ON CONFLICT(id) DO UPDATE SET canonical_role_name=excluded.canonical_role_name,
                 updated_at=excluded.updated_at""",
            (role_id,event_id,stage_id,work_id,role,Jsonb([]),proposal_id,
             CREATED_AT,CREATED_AT),
        )
    actors=[x for x in fixture.markers if x.kind=="ACTOR"]
    for index,marker in enumerate(actors):
        role=fixture.roles[index]
        actor_id=_account(connection,f"{fixture.key}.{marker.actor}",marker.name)
        advisory_id=stable_id(f"{fixture.key}:{marker.actor}:advisory")
        request_id=stable_id(f"{fixture.key}:{marker.actor}:request")
        item_id=stable_id(f"{fixture.key}:{marker.actor}:item")
        participation_id=stable_id(f"{fixture.key}:{marker.actor}:participation")
        connection.execute(
            """INSERT INTO participation_advisories(id,event_id,requester_account_id,
                 selections,availability,result,created_at)
               VALUES(%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT(id) DO UPDATE SET result=excluded.result""",
            (advisory_id,event_id,actor_id,Jsonb([{"actor_requirement_id":str(role_ids[role])}]),
             Jsonb({"availability_type":"FULL"}),
             Jsonb({"synthetic_demo":True}),CREATED_AT),
        )
        connection.execute(
            """INSERT INTO participation_requests(id,event_id,requester_account_id,status,
                 note,advisory_id,advisory_summary,idempotency_key,correlation_id,
                 created_at,updated_at)
               VALUES(%s,%s,%s,'APPROVED','Synthetic demo participation',%s,%s,%s,%s,%s,%s)
               ON CONFLICT(id) DO UPDATE SET status='APPROVED',updated_at=excluded.updated_at""",
            (request_id,event_id,actor_id,advisory_id,Jsonb({"synthetic_demo":True}),
             f"{FIXTURE_VERSION}:{fixture.key}:{marker.actor}:request",
             stable_id(f"{fixture.key}:{marker.actor}:request-correlation"),
             CREATED_AT,CREATED_AT),
        )
        connection.execute(
            """INSERT INTO participation_request_items(id,participation_request_id,
                 stage_id,work_id,actor_requirement_id,preference,availability_type,
                 status,created_at,updated_at)
               VALUES(%s,%s,%s,%s,%s,'PREFERRED','FULL','APPROVED',%s,%s)
               ON CONFLICT(id) DO UPDATE SET status='APPROVED',updated_at=excluded.updated_at""",
            (item_id,request_id,stage_id,work_id,role_ids[role],CREATED_AT,CREATED_AT),
        )
        connection.execute(
            """INSERT INTO participations(id,event_id,account_id,work_id,stage_id,
                 actor_requirement_id,approved_from_request_item_id,approved_start,
                 approved_end,status,created_at,updated_at)
               VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,'ACCEPTED',%s,%s)
               ON CONFLICT(id) DO UPDATE SET status='ACCEPTED',
                 actor_requirement_id=excluded.actor_requirement_id,
                 approved_start=excluded.approved_start,approved_end=excluded.approved_end,
                 updated_at=excluded.updated_at""",
            (participation_id,event_id,actor_id,work_id,stage_id,role_ids[role],item_id,
             fixture.start,fixture.start+timedelta(hours=6),CREATED_AT,CREATED_AT),
        )

    connection.execute(
        "DELETE FROM map_locations WHERE event_id=%s AND metadata->>'fixture'=%s",
        (event_id,FIXTURE_VERSION),
    )
    actor_ids={
        marker.actor:stable_id(f"account:{fixture.key}.{marker.actor}")
        for marker in actors
    }
    for marker in fixture.markers:
        metadata={
            "fixture":FIXTURE_VERSION,
            "synthetic_demo":True,
            "source_label":"Synthetic demo location — not live GPS",
        }
        if marker.organization:
            metadata["organization"]=marker.organization
        if marker.profession:
            metadata["profession"]=marker.profession
        entity_id=event_id if marker.kind=="EVENT" else actor_ids.get(marker.actor)
        connection.execute(
            """INSERT INTO map_locations(id,event_id,entity_type,entity_id,display_name,
                 latitude,longitude,area_label,location_precision,status,visible,
                 metadata,created_at,updated_at)
               VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,'DEMO',true,%s,%s,%s)""",
            (stable_id(f"{fixture.key}:marker:{marker.key}"),event_id,marker.kind,
             entity_id,marker.name,marker.latitude,marker.longitude,marker.area,
             marker.precision,Jsonb(metadata),CREATED_AT,CREATED_AT),
        )
    return {
        "fixture_key":fixture.key,
        "event_id":str(event_id),
        "event_name":fixture.name,
        "marker_count":len(fixture.markers),
        "actor_count":len(actors),
    }


def seed_demo_map(database: Database) -> dict[str, Any]:
    database.apply_schema()
    with database.connect() as connection:
        events=[_seed_event(connection,fixture) for fixture in EVENTS]
        counts=connection.execute(
            """SELECT entity_type,count(*) AS count FROM map_locations
               WHERE metadata->>'fixture'=%s GROUP BY entity_type ORDER BY entity_type""",
            (FIXTURE_VERSION,),
        ).fetchall()
    return {
        "fixture":FIXTURE_VERSION,
        "synthetic_demo":True,
        "events":events,
        "total_markers":sum(event["marker_count"] for event in events),
        "distribution":{row["entity_type"]:row["count"] for row in counts},
        "demo_sign_in":{
            "email":"ghasi-talab.organizer@demo.hatcommways.invalid",
            "password":DEMO_PASSWORD,
        },
    }


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url",
        default=os.environ.get("HATCOMMWAYS_DATABASE_URL"),
        help="PostgreSQL URL (or set HATCOMMWAYS_DATABASE_URL)",
    )
    args=parser.parse_args()
    if not args.database_url:
        parser.error("--database-url or HATCOMMWAYS_DATABASE_URL is required")
    print(json.dumps(seed_demo_map(Database(args.database_url)),indent=2,sort_keys=True))


if __name__ == "__main__":
    main()
