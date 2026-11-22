# DermaScan cutover runbook

Do not ship the replacement or remove the previous frontend until the gates below pass. Assign an owner for deployment, verification and rollback.

## 1. Prepare a backend pull request

- Record the production Render commit, configuration, database migration head and last known good frontend release. Branch from the actual production backend revision; compare it with the linked repository before applying changes.
- Review `utils/apply_backend_fixes.py` and port only the intended changes: estimated-score metadata, localized search and contribution upload validation. Apply the script only in a clean disposable checkout after reviewing its assumptions; inspect the complete diff before committing. Port the tests in `utils/backend-tests/` into the backend CI workflow. Do not copy credentials, generated artifacts or development configuration.
- Confirm the suitability route is registered in the candidate API. Include compatible source changes separately if production is behind. Compare candidate OpenAPI with production and verify both frontends against it. Do not bundle photo repair, data reprocessing or frontend deletion into this PR.
- Take a verified backup and rehearse restoring it to an isolated database. Review migration changes explicitly: if none are needed, run none. If required, use additive migrations that also support the previous backend release and rehearse them on staging first.

## 2. Validate on staging

- Deploy the candidate to a separate API and database with dedicated test accounts, storage and workers. Keep production credentials out of clients. Build the replacement against staging and confirm the old frontend still works with the candidate API.
- Test catalog pagination, search localization, real/estimated/missing scores, absent photos, barcode lookup, registration, refresh and sign-out, account switching, profiles, avoidance, suitability, routine CRUD and completion, recommendation replacement, label analysis and approved image contribution formats. Confirm invalid uploads are rejected and submitted jobs finish.
- Test physical iOS and Android devices, accessibility and permissions. Confirm existing accounts and records appear without copying or transforming data. Check whether users need to sign in again because of a different app identity or credential store; never export tokens to bridge this.
- Confirm store signing and bundle/package identifiers before submitting. To update the existing listing, use its existing identity and signing setup and a higher build number; verify the upgrade from an installed old build. For web, verify origin, CORS and service-worker cache updates.

## 3. Roll out and retain rollback

- Release the backward-compatible backend first. Smoke-test production with the old client and an authorized test account. Compare error rates, auth refresh failures, contribution queue backlog and API latency with the pre-release baseline.
- Roll out the new client to internal testers, then a limited production cohort before increasing exposure. Keep the old web artifact, backend deploy and mobile source/build pipeline available. Do not delete the old frontend during rollout; retain a tagged release and decide its retirement after the observation period.
- Halt expansion on account access failures, incorrect suitability, lost writes, elevated API errors or failed contribution processing. For web, restore the prior artifact and verify caching does not keep serving the new version. For mobile, pause rollout and ship a corrected higher-version build if needed; installed apps cannot be remotely downgraded. Keep the API compatible with both clients throughout.
- Roll back the backend to the recorded good revision only if it remains compatible with the deployed schema. Never restore over the live database as a routine rollback: doing so can discard writes made since the backup. Escalate data corruption separately and reconcile writes before a recovery restore.
