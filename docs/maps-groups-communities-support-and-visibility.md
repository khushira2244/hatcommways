# Hatcommways — Maps, Groups, Communities, Support, and Visibility

> Design/planning reference, not a deployed feature inventory. For current behavior and boundaries, see the [implementation documentation index](README.md). Broader capabilities below remain proposals unless confirmed there.

## 1. Purpose

This document defines how Hatcommways represents:

- temporary groups
- permanent communities
- organizations
- companies/sponsors
- public project discovery
- Action Maps
- Money / Support Maps
- Sponsor / Organization Maps
- optional demographic or distribution maps
- financial-support visibility
- payment-instruction privacy
- project-page visibility controls

This document is authoritative for community structure, map behavior, and support visibility.

Core principle:

> Hatcommways shows how communities are carrying a project through action and support without unnecessarily exposing private identities or financial information.

---

# 2. Community Structure

Hatcommways should not model every project as:

one creator
+
many unrelated users

Real-world execution often happens through:

- temporary groups
- permanent communities
- organizations
- companies
- local networks
- combinations of all of them

The platform must support these structures as first-class entities.

---

# 3. Temporary Groups

A Temporary Group exists primarily for a specific project or event.

Examples:

- Sunday Lake Cleanup Team
- Street Dog Shelter Jaipur Group
- School Robotics Workshop Team
- Neighborhood Tree Planting Group

A Temporary Group may be:

- created by a project creator
- created from project participants
- attached to one project
- attached to one event
- location-based
- invitation-based
- public or private

A Temporary Group may contain:

- members
- responsibilities
- organizers
- project discussions
- support information
- events
- project history

After project completion, a Temporary Group may:

- remain archived
- become inactive
- continue for follow-up work
- convert into a Permanent Community if members choose

Conversion must not happen automatically.

---

# 4. Permanent Communities

A Permanent Community exists beyond one event or project.

Examples:

- Indiranagar Animal Welfare Community
- Green Park Residents Group
- Local Makers Network
- School Alumni Volunteer Community
- Neighborhood Environmental Community
- City Accessibility Community

A Permanent Community may:

- create multiple projects
- maintain recurring members
- attach temporary groups
- carry community-level responsibilities
- participate in projects created by others
- maintain a community location or service area
- retain execution history where privacy allows

Permanent communities are not simply chat groups.

They exist as recurring execution networks.

---

# 5. Community Basis

A community may be based on one or more dimensions.

Examples:

- location
- shared interest
- social purpose
- institution
- profession
- school
- neighborhood
- welfare cause
- recurring activity
- project history

Location is important but should not be mandatory for every community.

---

# 6. Project Attachment

A Project may exist:

- independently
- under a Temporary Group
- under a Permanent Community
- under an Organization
- under a Company
- through collaboration between several of these

Examples:

Project A
→ Green Park Residents Community

Project B
→ temporary group only

Project C
→ NGO + temporary volunteer group

Project D
→ company + school + community

The platform must support multi-party participation.

---

# 7. Organizations

Organizations are persistent execution actors.

Examples:

- NGOs
- welfare groups
- schools
- nonprofits
- resident associations
- local clubs
- public-interest groups
- community bodies

Organizations may:

- create projects
- join projects
- provide representatives
- provide actors
- host events
- carry responsibilities
- communicate with project owners
- participate in maps where visibility permits

Organizations are not automatically public sponsors.

Their participation type must be explicit.

---

# 8. Companies / Sponsors

Companies are also persistent actors.

A company may participate by:

- sponsoring
- providing employees
- providing expertise
- providing equipment
- providing space
- organizing a project
- hosting an event
- taking responsibility for execution
- supporting communication
- supporting community work

Hatcommways must not reduce companies to money-only actors.

---

# 9. Sponsor Discovery Boundary

Hatcommways does not automatically search for sponsors on behalf of the project creator.

The creator/community is responsible for deciding:

- whether they want sponsors
- who they want to contact
- how they want to raise money

Companies may independently discover public projects.

Users may independently discover company/organization accounts.

Hatcommways may coordinate:

- contact requests
- email
- messaging
- meetings
- scheduling
- follow-ups
- commitments
- responsibility assignment

The relationship remains human-selected.

---

# 10. Funding Modes

A project may specify a Funding Mode.

Initial values:

- none_required
- self_funded
- group_funded
- community_funded
- sponsor_supported
- mixed

Funding mode describes the expected support model.

It does not imply that Hatcommways processes payments.

---

# 11. Funding Information

Where money is relevant, Hatcommways may store project financial state.

Potential internal values:

- target amount
- achieved amount
- remaining amount
- contribution source categories
- manually confirmed contributions
- support status

These values may have different visibility levels.

Core rule:

> Funding information is execution data, not automatically public fundraising data.

---

# 12. Payment Instructions

Hatcommways may store information explaining how an authorized participant can contribute.

Examples:

- UPI ID
- payment link
- organization payment page
- bank instructions
- payment contact information
- offline contribution instructions

Payment instructions exist only to tell an authorized person:

> How can I contribute?

Hatcommways initially does not:

- process the payment
- hold the money
- distribute the money
- independently verify the transaction

---

# 13. Payment Information Privacy

Payment instructions must be treated as sensitive.

They must not appear:

- on public maps
- in search indexing
- in public project metadata
- in public sponsor profiles
- in public API responses without authorization

Possible access levels:

- project owner only
- project admins
- project members
- approved contributors
- selected organization representatives

The exact permission model will be defined separately.

---

# 14. Target and Achieved Amount Visibility

The target amount and achieved amount should not automatically be public.

Possible visibility options:

- private to project admins
- visible to project members
- visible to attached community
- visible publicly if creator chooses
- visible only after completion

The system must not force live fundraising progress onto every project.

---

# 15. Public Support Representation

Even if exact financial numbers are private, Hatcommways may show aggregated support patterns when the creator permits it.

Examples:

- strong local community support
- sponsor participation exists
- several communities are contributing
- company support is active
- support is distributed across multiple areas

This powers the Money / Support Map.

---

# 16. Project Discovery Map

Hatcommways should provide a geographic discovery experience.

The discovery map answers:

> What are people trying to make happen around me?

Publicly discoverable project pins may show:

- project title
- broad location
- project category
- project status
- open actor opportunities
- event timing where applicable
- project visibility-safe support indicators

The public map should not expose precise private information.

---

# 17. Location Precision

Location visibility should be configurable.

Possible levels:

- country
- state/region
- city
- neighborhood
- approximate project area
- exact venue
- private exact location

Example:

Public:
Indiranagar, Bengaluru

Participants:
Exact meeting location

Exact location must not automatically be public.

---

# 18. Project Page Map System

A project/event page may contain several map views.

Normal projects should expose only a small number of meaningful views.

Recommended maximum:

- 2–3 map views for ordinary projects
- up to approximately 4 for large projects

The goal is clarity, not analytics overload.

---

# 19. Map Hierarchy

The initial map hierarchy is:

## Core

1. Action Map

## Conditional Core

2. Money / Support Map
3. Sponsor / Organization Map

## Optional Analytics

4. Age Distribution Map
5. Community Distribution Map
6. Contributor-Type Map
7. Geographic Segment Map
8. Other creator-approved aggregated maps

Not every project should expose every map.

---

# 20. Action Map

The Action Map is the foundational project map.

It answers:

> Who is helping execute this project, where is that action coming from, and what kinds of responsibilities are being carried?

Potential inputs:

- actor participation
- responsibility acceptance
- project members
- temporary groups
- permanent communities
- actor-role types
- task activity
- participant geography at an allowed precision

Possible views:

- participant density
- actor-role distribution
- community participation
- open responsibility areas
- execution-strength distribution
- geographic participation
- active vs unfilled execution regions

---

# 21. Action Strength

Action Map visual strength should represent execution participation.

Potential signals:

- number of active actors
- number of accepted responsibilities
- role coverage
- active task participation
- community involvement

It should not simply represent:

- page views
- likes
- passive interest

Core principle:

> Action strength measures participation in execution, not attention.

---

# 22. Action Map Example

Example project:

Restore a neighborhood playground.

Action Map may show:

Area A:
strong participation

Area B:
medium participation

Area C:
few participants

Role view:

- Organizers: 3
- Executors: 18
- Specialists: 2
- Reviewers: 1
- Open roles: 4

A visitor can understand:

> Where is execution strong?
> What responsibilities are still open?
> How can I participate?

---

# 23. Money / Support Map

The Money / Support Map represents financial support patterns around a project.

It answers:

> How are people, communities, and organizations financially supporting this project?

It is not a payment interface.

It is not a donor list.

It is an aggregated visualization.

---

# 24. Money Map Inputs

Potential inputs include:

- manually confirmed contribution amount
- contributor area
- contributor type
- community affiliation
- sponsor/company affiliation
- anonymous/public attribution setting
- contribution visibility permission

Only privacy-safe data may be included.

---

# 25. Money Map Views

Possible Money Map modes:

## Area View

Shows which geographic areas are contributing.

## Community View

Shows contribution strength by community/group.

## Contributor-Type View

Examples:

- individuals
- temporary groups
- permanent communities
- organizations
- companies/sponsors

## Support Strength View

Shows relative financial-support intensity.

These views may be selectable from the same Money Map.

---

# 26. Money Strength

A stronger visual point may represent greater aggregated financial support from that segment.

However:

> Bigger financial contribution must not automatically mean greater social importance.

The map is informational.

It should not create a donor ranking or social hierarchy.

---

# 27. Public Money Map Privacy

Public Money Map must not expose:

- exact payment address
- UPI ID
- bank details
- private donor name without consent
- transaction identifier
- private receipt
- exact location of an individual donor
- sensitive demographic combination that could identify a person

Public data should be aggregated.

---

# 28. Money Map and Participation Motivation

The Money Map may help visitors understand that a project has community support.

Example:

- residents from 5 nearby areas are contributing
- 3 community groups are participating financially
- 2 companies have chosen to support the event

This may encourage additional participation or financial support.

That is acceptable.

The map should not use manipulative countdowns or artificial pressure.

---

# 29. Action and Money Maps Together

Action and Money Maps tell different stories.

Example:

Project A:

Action strength:
high

Money support:
low

Interpretation:

Many people are willing to execute, but financial support may be insufficient.

Project B:

Action strength:
low

Money support:
high

Interpretation:

Financial support exists, but execution actors are still missing.

These two maps together provide meaningful project intelligence.

---

# 30. Sponsor / Organization Map

The Sponsor / Organization Map represents organizational participation in a specific project.

Possible entities:

- companies
- NGOs
- welfare groups
- schools
- resident organizations
- local organizations
- community groups

The map may show:

- organization location
- participation type
- support type
- execution role
- sponsor involvement
- organization intensity

---

# 31. Organization Participation Types

An organization may participate as:

- project owner
- organization partner
- event host
- task owner
- specialist provider
- volunteer provider
- sponsor
- reviewer
- coordinator
- venue provider
- other execution role

The UI should not imply that every organization marker means sponsorship.

---

# 32. Sponsor Visibility

A sponsor may choose project-level attribution.

Potential visibility states:

- anonymous/private
- project participants only
- visible on project/event page
- visible in public map layer
- selected public highlight

Full sponsor history should remain private unless explicitly published.

---

# 33. Recognition Follows the Work

Sponsor/company recognition should primarily appear on the project/event that was supported.

Example:

Community Garden Restoration

Supported by:
Company X

Contribution:
project-approved public summary

Outcome:
completed

Public users should not automatically be able to open Company X and inspect all historical contributions.

Core rule:

> Recognition follows the work, not the sponsor profile.

---

# 34. Sponsor Private Impact Map

A company/sponsor may have a private impact map.

This map can aggregate its own participation across projects.

Possible data:

- projects supported
- locations
- contribution amount
- support type
- responsibilities enabled
- participants involved
- people/community affected
- project outcomes
- appreciation generated

This is private organizational intelligence.

It should not automatically become public.

---

# 35. Organization Private Map

Non-sponsor organizations may also benefit from a private participation map.

Example:

Animal welfare group sees:

- projects joined
- volunteers deployed
- events participated in
- regions served
- responsibilities carried
- completed outcomes

This is not limited to companies.

---

# 36. Appreciation and Thank-You Data

Completed projects may generate:

- thank-you messages
- appreciation notes
- outcome summaries
- organization acknowledgements
- sponsor acknowledgements

These belong to the project history.

A project may send approved messages to participating organizations.

AI may help draft these messages.

Humans approve them where appropriate.

---

# 37. Optional Analytics Maps

A creator may enable additional project-map views.

Possible examples:

- age bands
- community types
- participant types
- local vs outside-area participation
- first-time vs recurring contributors
- organization category
- role distribution

These are optional analytics.

They are not required for execution.

---

# 38. Age Distribution Map

Age-related maps require additional caution.

Use broad age bands.

Examples:

- 18–24
- 25–34
- 35–44
- 45–59
- 60+

Do not display exact ages publicly.

Do not display age maps when the group size is too small to preserve anonymity.

The creator must explicitly enable this view.

---

# 39. Small-Group Privacy Thresholds

Aggregated demographic maps should use minimum-count thresholds.

Example:

If only 2 people exist in one age/location segment, do not expose that segment publicly.

Possible behavior:

- merge into "Other"
- hide the segment
- increase geographic aggregation
- disable the map

Exact thresholds will be defined in the privacy architecture.

---

# 40. Community Distribution Map

Community Distribution may show:

- temporary groups
- permanent communities
- neighborhoods
- schools
- organizations
- other project-relevant group categories

This may help show:

> Which communities are carrying this project?

This is optional unless the project explicitly centers on multi-community collaboration.

---

# 41. Map Approval

Project creators/admins should control which optional maps become visible.

Conceptual map settings:

Action Map:
enabled by default where location data permits

Money / Support Map:
enabled when relevant and approved

Sponsor / Organization Map:
enabled when relevant and approved

Age Distribution:
disabled by default

Community Distribution:
optional

Other demographic analytics:
disabled by default

---

# 42. Core vs Optional Visibility

Not every map is treated equally.

## Core Product Map

Action Map

## Contextual Core Maps

Money / Support
Sponsor / Organization

## Optional Maps

Demographic and analytical views

The system should not require project owners to manually configure dozens of map settings.

Defaults must remain simple.

---

# 43. Map Visibility States

A map may have visibility such as:

- private
- project members
- attached community
- registered Hatcommways users
- public

Individual map layers may have separate visibility.

Example:

Action Map:
public

Money Map:
community only

Age Map:
disabled

Sponsor Map:
public

---

# 44. Map Data Versions

Maps reflect dynamic execution state.

Their data changes when:

- actors join
- responsibilities change
- contributions update
- organizations join
- locations change
- project visibility changes

Map data may therefore have version/timestamp metadata.

Do not treat map output as permanent truth.

---

# 45. Real-Time vs Periodic Maps

Not every map needs immediate real-time recomputation.

Possible approaches:

Action Map:
near-real-time

Money Map:
update after manual contribution confirmation

Demographic maps:
periodic aggregation

Sponsor private impact map:
event-driven or periodic aggregation

Implementation should balance:

- freshness
- cost
- privacy
- complexity

---

# 46. Public Interest vs Execution

Hatcommways may later understand passive public interest.

Examples:

- project views
- follows
- saves
- shares

However, these signals must remain separate from Action Map execution strength.

Core rule:

> Interest is not action.

A project with many views but no responsibilities accepted should not look execution-strong.

---

# 47. Participation Types

Project participation may broadly include:

- responsibility carrying
- task execution
- event attendance
- organizational participation
- financial support
- advisory involvement
- passive interest

Maps should clearly distinguish these categories.

---

# 48. Project Page Map Selector

A project page may expose a small map selector.

Example:

[ Action ]
[ Support ]
[ Organizations ]

Optional large-project view:

[ Community ]

Do not create a crowded menu with many simultaneous maps.

---

# 49. Map Storytelling

Maps are not only analytics.

They help a visitor understand:

- whether people care enough to act
- where participation is forming
- which communities are involved
- how execution is distributed
- how support is distributed
- where more help may be useful

Maps should tell the project's living execution story.

---

# 50. Public Project Page

A public project/event page may contain:

- goal
- project story
- location at approved precision
- timeline/progress
- open actor responsibilities
- active actor roles
- upcoming events
- Action Map
- approved Support Map
- approved Organization Map
- selected project updates
- public outcome information
- project-level sponsor recognition

It should not expose sensitive internal data.

---

# 51. Member Project View

Project members may additionally see:

- detailed timeline
- private task status
- internal responsibilities
- group communication
- private support/funding state
- approved payment instructions
- exact locations where authorized
- internal events
- blocker information
- project decisions

---

# 52. Project Admin View

Admins may additionally access:

- project visibility settings
- map visibility settings
- payment instruction management
- funding state updates
- participant management
- organization participation controls
- map aggregation settings
- privacy review
- publication controls

---

# 53. Manual Contribution Updates

Because Hatcommways does not initially process payments, contribution records may be manually updated.

Possible states:

- pledged
- reported
- confirmed_by_project
- cancelled

The UI must clearly communicate that:

> confirmed_by_project

does not mean independently verified by Hatcommways.

---

# 54. Support Data and Execution

Funding/support data may affect execution state.

Example:

Task A:
does not require money

Task B:
requires project support state = sufficient

If funding is insufficient:

Task B waits.

Task A continues.

Financial state must not automatically block unrelated work.

---

# 55. Group-Level Support

A temporary or permanent group may contribute collectively.

Example:

Green Park Residents:
₹20,000

This may appear as:

community contribution

rather than exposing every individual member.

The group may decide whether individual contributions are visible internally.

---

# 56. Company-Level Support

A company may contribute as one organizational entity.

Example:

Company X:
supporting materials branch

The project may record:

- organization
- support type
- manually confirmed amount where applicable
- public attribution state

Public maps need not expose internal corporate details.

---

# 57. Mixed Support

Projects may combine:

- creator money
- community money
- company sponsorship
- organization support
- non-financial support

Hatcommways should not assume a single source.

Example:

Project Funding Mode:
mixed

Sources:

Community:
40%

Company:
30%

Creator:
30%

Exact numbers may remain private while aggregated public views remain enabled.

---

# 58. Non-Financial Support

Although this document focuses heavily on maps and money support, organizations may contribute non-financial support.

Examples:

- expertise
- venue
- employees
- equipment
- services
- logistics

These contributions may appear in organization participation views rather than Money Map.

Do not convert all support into monetary values.

---

# 59. Map Privacy Invariants

## Invariant 1

Payment instructions are never public by default.

## Invariant 2

Exact donor identity is never inferred from aggregated map data.

## Invariant 3

Exact user location is never exposed merely because a project uses maps.

## Invariant 4

Action strength is not the same as public interest.

## Invariant 5

Money strength is not a social ranking.

## Invariant 6

Sponsor history is not automatically public.

## Invariant 7

Optional demographic maps require explicit creator approval and privacy-safe aggregation.

## Invariant 8

Maps are views over governed project data, not independent truth sources.

## Invariant 9

Organizations are not assumed to be sponsors.

## Invariant 10

Public recognition remains project-centric.

---

# 60. Deterministic vs Agentic Responsibilities

Deterministic application logic should handle:

- map visibility permissions
- geographic aggregation
- contribution aggregation
- group membership
- community membership
- organization relationships
- funding-state persistence
- payment-detail access control
- minimum privacy thresholds
- public/private field filtering

Agents may help with:

- interpreting participation patterns
- summarizing project support
- identifying meaningful map narratives
- suggesting which maps may be useful
- drafting appreciation/outcome summaries
- understanding where execution participation is weak
- reasoning about support-related execution blockers

Agents must not override privacy rules.

---

# 61. Core Community Model

Conceptually:

Participants
→ form
Temporary Groups / Permanent Communities

Groups / Communities / Organizations
→ participate in
Projects

Projects
→ create
Execution Activity

Execution Activity
→ feeds
Action Map

Financial Support
→ feeds
Money / Support Map

Organization Participation
→ feeds
Sponsor / Organization Map

Optional Aggregated Attributes
→ feed
Analytics Maps

Visibility + Privacy Policy
→ controls
What each viewer can see

---

# 62. Final Principle

Hatcommways should make community participation visible without turning people into public data points.

The project page should help visitors understand:

> Who is acting?
> How is the community supporting the work?
> Which organizations are involved?
> Where can I participate?

At the same time, the system must preserve:

- personal privacy
- payment privacy
- organization privacy
- project-controlled visibility

The maps exist to make collective execution understandable.

They are not surveillance, donor leaderboards, or engagement dashboards.