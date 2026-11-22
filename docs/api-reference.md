# Interactive API documentation

When running in Development (the default launch profiles), open
`https://localhost:7231/scalar` for Scalar API documentation. The OpenAPI document
is available at `https://localhost:7231/openapi/v1.json`.

All current endpoints include descriptions and response examples:
`GET /api/aed/owners`, `GET /api/aed/nearest`, `GET /api/aed/nearest({count})`, `GET /api/translations/profiles`,
`GET /api/translations/profiles({name})`, `POST /api/translations/profiles`,
`POST /api/translations/profiles({name})/import`,
`POST /api/zgloszenia`, and `GET /weatherforecast`. The profile endpoint also includes an editable JSON
request example and examples of `400` validation and `409` duplicate-name errors.
Scalar generates request snippets and lets you send requests to the running app;
POST requests create real database records, so use a new profile name for each
successful request.

Scalar and the OpenAPI document are not exposed outside Development.

