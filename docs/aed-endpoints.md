# AED endpoints

## AED lists and data statistics

`GET /api/aed` returns every AED (coordinates, owner and address, access, hours, `DataRating`,
`LastUpdated`), `GET /api/aed/valid` only those with `DataRating = Fine`, and
`GET /api/aed/statistics` returns `total`, `valid`, `missingData`, `unknown` (NULL rating) and
`validPercentage = valid / total * 100` (two decimals). The GUI's "Weryfikacja danych" tab shows this value.

`POST /api/aed/validate` (Maintainer or Admin) goes through every AED and applies the data standard:
**location** (latitude and longitude), **address** (city, street, postal code, building number), **name**
(the owner's name; an AED has none of its own), **access** and both **availability hours** must be known.
Anything missing marks the AED `MissingData`, a complete one `Fine`; changed rows get a new `LastUpdated`.
`?dryRun=true` only reports. The response lists `checked`, `valid`, `missingData`, `changed`, how many AEDs miss
each group, and the first 100 invalid AEDs with what they miss. Accepting a report uses the same standard.

The upgrade scripts must be applied before these endpoints work on an existing database
(`DataRating` comes from `014-aed-data-rating.sql`).

## Find the nearest available AED

```powershell
curl.exe "https://localhost:7231/api/aed/nearest?latitude=52.229676&longitude=21.012229"
```

Both query coordinates are required, finite decimal degrees within latitude
[-90, 90] and longitude [-180, 180]. The database ranks eligible AEDs by
great-circle (straight-line, not walking/driving) distance; it does not load all
AEDs into application memory. Equal distances choose the lowest AED ID.

An eligible AED has both coordinates, is not marked `Private`, and is not known
to be closed. `Open`, `Emergency`, and unknown access are included. Complete
daily opening hours are checked against the current **Europe/Warsaw** time,
including daylight-saving changes. Opening is inclusive and closing exclusive;
overnight ranges such as 22 to 6 work across midnight. If either hour is
unknown, availability is treated as unknown and the AED is included. Ratings
and an owner's public/private flag do not override these access rules.

Example response:

```json
{
  "id": 1,
  "latitude": 52.229676,
  "longitude": 21.012229,
  "ownerName": "Example operator",
  "cityName": "Warszawa",
  "streetName": "Example Street",
  "postalCode": "00-001",
  "buildingNumber": 10
}
```

Unknown or blank owner/address text, and unknown building numbers, are omitted
from the response. An AED without an owner or address still returns its ID and
coordinates. Invalid query coordinates return `400`; no eligible AED returns
`404`.

To request multiple nearest available AEDs, pass a positive 32-bit integer in
parentheses in the route (not as a query parameter):

```powershell
curl.exe "https://localhost:7231/api/aed/nearest(5)?latitude=52.229676&longitude=21.012229"
```

This returns an array of up to five AEDs, closest first, using the same
availability and metadata rules. Ties use AED ID. The limit is applied in the
database. If fewer AEDs are available, all eligible AEDs are returned; if none
are available, the response is `200` with `[]`. Invalid counts or coordinates
return `400`. The existing single-AED endpoint is unchanged.

For an existing database, run `.\scripts\Initialize-Database.ps1` to apply
`008-aed-owner.sql`. Existing AEDs retain unknown ownership (`NULL`); no
historical owner is inferred from location. Reimport CSV data with owner
mappings, such as `openaedmap-2`, to populate these explicit links.

