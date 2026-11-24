# Dev 3 integration notes

The personal library, dermatologist guidance, and routine sharing features are integrated on
`dev3-Library_&_Guidance`.

## Backend registration

`backend/src/app/api/v1/router.py` mounts the personal library under `/library` and guidance under
`/dermatologists`. Routine share operations extend the already-mounted routines router.

`backend/migrations/env.py` registers the dermatologists and personal library model modules. The
additive migration `20261123_0014_dev3_library_guidance.py` follows `20261111_0013`; it creates the
feature tables and seeds English and French AAD guidance. This checkout has one Alembic head at
`20261123_0014`. Recheck heads when combining other sprint branches and add a merge revision if
they introduce parallel heads.

## API contract

The contract was regenerated from the integrated FastAPI application with
`backend/scripts/export_openapi.py`, producing `docs/openapi.json` and `mobile/openapi.json`. Mobile
types were regenerated with `npm run api:types` from `mobile/`. Feature response aliases in
`mobile/lib/api/types.ts` use the generated schema components. The checked-out app still uses its
existing `request<T>` client in `mobile/lib/api/client.ts` rather than the `openapi-fetch` client
described in the sprint allocation; the feature types and endpoint paths now follow the generated
contract.

## Verification guide

See [Dev 3 feature test guide](dev3-test-guide.md) for automated gates, migration instructions, API
coverage, and manual mobile flows.
