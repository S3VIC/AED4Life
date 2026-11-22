# Users and AED reports

`Users` contains an auto-generated `Int64` `Id`, a required unique `Username`
(up to 255 characters), required `FirstName`, `LastName`, `BirthDate` (`DATE`,
mapped to `DateOnly`), required residence `AddressId` referencing `Addresses`,
and required `Type`. Types are stored as integers: `Admin=0`, `Normal=1`,
`PublicRepresentative=2`, `Maintainer=3`. New C# users default to `Normal`;
SQL inserts must specify the type. Usernames follow the database's
case-insensitive collation.

`PasswordHash` is required (`VARCHAR(512)`, nonempty) and excluded from JSON.
Store only the output of the registered `IPasswordHasher<User>`, never a
plaintext password or reversible encryption. It uses ASP.NET Core Identity V3
PBKDF2-HMAC-SHA512 with 210,000 iterations and a separate random salt per hash;
the format includes the version, algorithm, iteration count, salt, and subkey.
The framework password hasher is registered for future registration/login
handlers; those endpoints are not implemented yet.

Before saving a newly registered user, hash the password supplied in a separate
registration request DTO:

```csharp
user.PasswordHash = passwordHasher.HashPassword(user, providedPassword);
```

Verify passwords using `VerifyHashedPassword(user, user.PasswordHash, providedPassword)`,
not string comparison or by hashing again. Treat `Failed` as a failed login;
when verification returns `SuccessRehashNeeded`, generate and save a new hash.
Never return password hashes in API responses or log plaintext passwords.

`010-user-password-hash.sql` upgrades existing databases. If any existing user
lacks a hash, initialization **stops** with an explicit error. The upgrade
leaves a temporary nullable `PasswordHash` column so an operator can provision
each user's hash through trusted code using the application password hasher.
Rerun initialization after provisioning all users; it enforces `NOT NULL` and
rejects empty hashes without modifying supplied hashes. Do not assign a shared
default password or use SQL `MD5`/`SHA` functions for password storage.
Initialization creates a bootstrap `admin` account (`Type=Admin`) whenever
that username is absent, even when other users already exist. Its dummy profile
is Jan Kowalski, born 1980-01-01, linked to the first existing address.
The requested initial password is stored only as an Identity V3 hash. This is
a publicly known, weak bootstrap credential: change it before exposing the app.
An existing `admin` account is never overwritten, including its password,
profile, and type. Other demo users have hashes of discarded random passwords.
Registration/login endpoints are still not implemented by this seed.

`AEDReports` contains an auto-generated `Int64` `Id`, required author `UserId`
referencing `Users`, optional `AEDId` referencing `AEDs`, required nonblank `PhotoUrl`
(a URL or file path, not image bytes), required nonblank device-placement
`Description`, optional `AvailabilityStartHour`/`AvailabilityEndHour`, optional
`IsPubliclyAccessible`, optional integer `Rating` (0-100 inclusive), required `Created` and `LastUpdated`
timestamps, and required `Status`: `Submitted=0`, `UnderReview=1`,
`Confirmed=2`, `Rejected=3`. A report may concern an AED not yet in the database.
Reports can upload photos using the endpoint below; seeded photo paths are placeholders.
SQL rejects null, empty, and whitespace-only paths, including spaces, tabs,
and newlines. The database does not check whether the external file exists,
contains bytes, or is a valid image. Uploaded files are checked separately by the endpoint.
`011-required-report-photo.sql` stops initialization if any existing report has
an invalid path. Supply valid image paths for those reports and rerun the
initializer; no paths or reports are fabricated, deleted, or replaced by the upgrade.
`012-report-placement-metadata.sql` adds the placement fields. Existing reports
without a nonblank description receive the explicit placeholder
`Legacy report: device placement description was not provided.`
Existing descriptions, opening hours, accessibility flags, and other report data
are preserved on reruns; new optional fields remain `NULL` when unknown.
`013-report-rating.sql` adds the nullable rating and enforces the inclusive
0-100 range without assigning ratings to old reports or changing known ratings.
Report ratings are independent of the existing AED `DataRating` enum.
Optional `ReporterLatitude`/`ReporterLongitude` record the reporter's GPS separately
from the AED location snapshot: `Latitude`, `Longitude`, `CityName`, `StreetName`,
`PostalCode` (up to 6 characters), and integer `BuildingNumber`.
`015-report-location.sql` adds these nullable columns and coordinate checks without
inventing locations for existing reports. Known snapshots are preserved on reruns.
As with AED timestamps, application code supplies and updates report timestamps
in UTC, with microsecond database precision.

Foreign keys restrict deletion of referenced users, AEDs, and residence
addresses. SQL checks reject undefined user types and report statuses. These
tables and their EF entities do not add authentication or authorization.

For an existing database, run either initializer from the [README](../README.md#fill-empty-tables) to apply
`009-users-and-aed-reports.sql`, `010-user-password-hash.sql`,
`011-required-report-photo.sql`, `012-report-placement-metadata.sql`, and
`013-report-rating.sql` and `015-report-location.sql`, then seed empty tables without replacing
existing records.

## Creating a report

`POST /api/zgloszenia` accepts **multipart/form-data**, including when there is
no uploaded file. The `metadata` field is a JSON object encoded as a string:
required positive `userId`, required nonblank `description` of where the device
is or could be placed, optional positive `aedId`, and optional `photoUrl`.
The referenced user/AED must exist. Provide exactly one image source: a
nonblank `photoUrl` or the optional file field `image`.
Of the new placement fields, only `description` is mandatory; the existing
author and photo requirements are unchanged. Descriptions are trimmed.
Optional `availabilityStartHour` is an integer from 0 to 23, and
`availabilityEndHour` is an integer from 0 to 24. Either may be omitted or null
independently. Complete ranges must have different bounds; overnight ranges
such as 22-6 are allowed, and 0-24 means all day. Optional
`isPubliclyAccessible` is `true` when anyone can access the device, `false` when
access is restricted, or null/omitted when unknown. These are report details;
submitting them does not automatically update an existing AED.
Optional `rating` must be a whole number from **0 to 100** inclusive; omit it
or use null when unknown. Fractions, invalid types, and out-of-range values
return `400`. Only description is mandatory among these new report details.

Optional `reporterLatitude` and `reporterLongitude` must be supplied together;
omit both or set both to null when the reporter's GPS is unknown. All coordinates
must be finite numbers, with latitude in **[-90, 90]** and longitude in
**[-180, 180]**.

An explicit `aedId` takes precedence, even if it is far from the reporter.
Otherwise, the endpoint links the nearest AED **within 100 meters** of the
reporter's GPS using great-circle distance; equal distances select the lowest
AED ID. This includes private and closed devices: reporting a device does not
require it to be currently available. Devices without both coordinates cannot
be matched automatically.

Optional `latitude`, `longitude`, `cityName`, `streetName`, `postalCode` (at most
6 characters), and integer `buildingNumber` describe the **AED**, not the
reporter. Known fields from the linked AED and its address take precedence;
only missing fields fall back to request values. Address text is trimmed and
blank text becomes null. Location fields may be omitted or null, including
independently unknown AED coordinates. The resolved location is stored as a
snapshot on the report. When nothing matches, the supplied location stays on
the report with `aedId: null`; no AED or address is created or modified.
Reporter GPS is never silently substituted for missing AED coordinates.
Requests without location fields remain supported.

```powershell
curl.exe "https://localhost:7231/api/zgloszenia" `
  --form 'metadata={"userId":1,"aedId":1,"description":"On the wall beside reception.","availabilityStartHour":8,"availabilityEndHour":20,"isPubliclyAccessible":true,"rating":85}' `
  --form 'image=@C:\photos\aed.png'
```

Without uploading a file:

```powershell
curl.exe "https://localhost:7231/api/zgloszenia" `
  --form 'metadata={"userId":1,"description":"Inside the main entrance.","photoUrl":"https://example.test/photos/aed.jpg","reporterLatitude":52.2297,"reporterLongitude":21.0122,"latitude":52.229676,"longitude":21.012229,"cityName":"Warszawa","streetName":"Example Street","postalCode":"00-001","buildingNumber":10}'
```

Uploads must be nonempty PNG/JPEG files, at most **5 MiB (5,242,880 bytes)**.
The endpoint checks file signatures, not the client-supplied filename/MIME type;
it does not fully decode or re-encode images. Files are stored under generated
GUID filenames, never under the supplied filename. Unknown metadata fields
(including client-supplied status, timestamps, or report ID) are rejected.
Metadata is limited to 16,384 characters; total multipart requests are limited
to 5 MiB plus 128 KiB of form overhead.

The server sets both timestamps to the current UTC time and status to
`Submitted`. A successful request returns `201` with `id`, `userId`, `aedId`,
`photoUrl`, `description`, `availabilityStartHour`, `availabilityEndHour`,
`isPubliclyAccessible`, `rating`, `created`, `lastUpdated`, `status`,
`reporterLatitude`, `reporterLongitude`, `latitude`, `longitude`, `cityName`,
`streetName`, `postalCode`, and `buildingNumber`. Unknown location fields are null.
Uploaded `photoUrl` values
are filenames relative to the configured storage directory, **not public image
URLs**. No image-download endpoint is exposed. Supplied external paths/URLs
are trimmed but never fetched; their file contents cannot be validated here.
Invalid requests return `400`, unsupported image signatures/content types
`415`, oversized uploads `413`, database conflicts `409`, and storage failures
`503`. Failed saves remove files written by that request; cleanup failures are
logged. Database records and uploaded files must be backed up together.

**Prototype identity:** `userId` is supplied by the caller, not authenticated.
Anyone able to access this endpoint can submit as any existing user. Protect
the API before public deployment and derive the author from authentication
when login is implemented. No cookie authentication is used; multipart
antiforgery checks are disabled consistently with the CSV upload endpoint.

## Report image storage

By default, images are saved in `App_Data/report-images` under the API's
content-root directory (outside `wwwroot` and ignored by Git). Override with
`ReportImages:Directory`, for example:

```powershell
$env:ReportImages__Directory = 'C:\aed4life-data\report-images'
```

The API process must have write access. Storage must remain outside the web
root. When containerizing the API, set `ReportImages__Directory` to
`/data/report-images` and mount a persistent named volume or bind mount at that
directory **on the API container**, not MariaDB. The current Compose file still
runs only MariaDB; no API service or volume is added automatically.

