# Maps and visibility

[Documentation index](README.md) · [Detailed event-map model](map-read-model.md)

| Map | Data and behavior |
| --- | --- |
| Explore | Real public events; name/location/category discovery; geolocation centers UX without blocking remote search/joining. |
| Event / actor | Permitted operational locations subject to visibility rules; not universal live tracking. |
| Sponsor | Approved contributions on PUBLIC events with sponsor visibility enabled; existing coordinates; fitted bounds or a sensible single-event zoom. |

`apps/web/event-map.js` supplies the Google Maps loader. Generated browser config supplies key/map ID. Missing configuration/locations produces a fallback; cards and links remain. Browser geolocation is discovery UX, not a participant record or database location feed.

My Sponsorships uses a server-side public projection. Pending/rejected offers and private comments are absent for other viewers. Public sponsor view currently requires authentication. Missing profile images use initials; no uploaded/verified profile is invented.
