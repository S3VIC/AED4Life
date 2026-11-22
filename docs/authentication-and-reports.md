# Authentication, roles and report review

`POST /api/login` takes `{"username","password"}` and verifies the password against the stored
Identity V3 PBKDF2 hash (a rehash is saved when the hasher asks for one). Unknown users and wrong
passwords both return `401`; logins are rate limited to 10 per minute per client address (`429`).
Success returns a bearer token (`accessToken`, valid 8 hours): send `Authorization: Bearer <token>`.
Tokens are protected with ASP.NET Core Data Protection keys, so they stop working when those keys
change (for example after a restart without persisted keys); log in again.

| Endpoint | Access | Purpose |
| --- | --- | --- |
| `GET /api/me` | any logged-in user | Id, username, name and type, read from the database on every call |
| `GET /api/users` | Admin | All users without hashes |
| `POST /api/users/{id}/promote` | Admin | `Normal`/`PublicRepresentative` → `Maintainer`; idempotent for maintainers, `409` for admins |
| `GET /api/zgloszenia?status=` | Maintainer, Admin | Newest 200 reports, optionally by status |
| `POST /api/zgloszenia/{id}/accept` | Maintainer, Admin | Confirm the report and update the main AED data (below) |
| `POST /api/zgloszenia/{id}/reject` | Maintainer, Admin | `Submitted`/`UnderReview` → `Rejected`; AED data untouched |

Roles are checked against the database on each request, so promotions and demotions apply
immediately. `POST /api/zgloszenia` itself is unchanged (still takes `userId` in its metadata).

**Accepting a report** runs in one serializable transaction. The linked AED is updated, or a new AED is
created from the report's coordinates when none is linked (a report with neither is rejected with `409`).
Cities, streets, postal codes and the address are found or created (report values win; parts it does not
know are kept). `isPubliclyAccessible` maps to `Access` (`true` → `Open`, `false` → `Private`), availability
hours and coordinates are copied when supplied, and `DataRating` is recomputed with the data standard in
`AEDDataStandard`: **`Fine`** when coordinates, a complete address (city, street, postal code, building
number), `Access` and both availability hours are known, otherwise **`MissingData`**. The owner is optional.

