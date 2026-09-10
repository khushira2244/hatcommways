# Event map read model

GET /events/{event_id}/map is an authenticated, read-only projection for a
future map UI. It returns the event, visible persisted markers, filter values,
and the event's map settings. Reading it does not generate plans, invoke an
agent, geocode an address, or mutate event state.

Marker types are bounded to EVENT, ACTOR, RESOURCE, SPONSOR,
SUPPORT_PARTNER, ACCESS_POINT, PARKING, MEETING_POINT, TRANSPORT,
and OTHER. Location precision is bounded to EXACT, APPROXIMATE, ZONE,
and DEMO_APPROXIMATE.

The projection applies these authority and privacy rules:

- A private event is available only to an active event member or an accepted
  participant. Public and unlisted events still require an active account.
- Actor markers are limited to accepted participations and require the event's
  map and actor-tree visibility settings. Exact actor markers are suppressed
  because the current data model has no explicit actor consent for exposing
  exact coordinates.
- Resource markers must match an authoritative Event Setup resource and obey
  resource visibility.
- Sponsor and support-partner markers must match a visible Event Setup entry
  of the same type and obey sponsor visibility.
- Marker metadata uses a small public allowlist. Arbitrary stored metadata is
  never copied into the response.
- Rows from other events cannot enter the projection.

Locations are stored explicitly in map_locations; the service never invents
coordinates from Event Setup text. A later write workflow can manage those
records after its authorization and consent rules are defined.

The response exposes filter values for marker type, area, role, organization,
profession, and resource type. Empty dimensions remain present as empty lists,
which gives a frontend a stable contract without requiring Google Maps or any
other map provider.

## Deterministic demo fixture

Seed the four synthetic hackathon events into a local database with:

    python -m services.planning_foundation.demo_map_seed --database-url postgresql://postgres@127.0.0.1:5432/hatcommways

The command prints the stable event IDs, marker counts, distribution, and demo
organizer sign-in. It is safe to repeat: authoritative rows use stable UUID5
identities, while only map rows carrying the fixture's synthetic tag are
replaced. The dataset contains no home addresses, live GPS, or participant
health information.

## Google Maps development configuration

Set the browser-restricted Google Maps JavaScript API key on the API process:

    $env:HATCOMMWAYS_GOOGLE_MAPS_API_KEY="your-browser-restricted-key"
    $env:HATCOMMWAYS_GOOGLE_MAPS_MAP_ID="your-map-id"
    uvicorn services.api.main:app --reload

The authenticated web configuration endpoint supplies the key to the shared
Event Home map loader. Keep HTTP referrer and API restrictions enabled in
Google Cloud. The shared component uses Google's recommended Advanced Marker
API. If either variable is absent, Event Home and Actor Dashboard show a
contained configuration message and continue rendering the rest of the page.
