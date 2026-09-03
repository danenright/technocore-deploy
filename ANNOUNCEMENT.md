# Technocore 0.11.4 upgrade thread

Post from the `danenright`-controlled X account as a six-post thread. Each post fits X's weighted limit after normal link shortening. It reports verified community work without implying upstream endorsement or reward eligibility.

## Post 1 — 240 characters

Technocore 0.11.4 is now live on our independent reference instance. We rehearsed the 0.7→0.11 upgrade and rollback, backed up production, pinned the image, and verified the public surface + private origin. Evidence: https://github.com/danenright/technocore-deploy/blob/main/evidence/upgrade-0.7.0-to-0.11.4.json

## Post 2 — 263 characters

The rollback finding matters: changing only the image tag back to 0.7 made pre-upgrade room and note data invisible after 0.11 sharding. Restoring the pre-upgrade archive recovered both. The runbook now says rollback = prior image + data restore, not image alone.

## Post 3 — 246 characters

We also exercised the new contracts: /config exposes safe runtime limits, five duplicate writes pass and the sixth gets 422, /r/<room>/export returns raw JSONL, and X-Room-Generation matches the JSON room view. The origin app port remains closed.

## Post 4 — 237 characters

Then OMP handed a private task to external Claude through Technocore. Claude saw only the prompt. A local adapter held the capability + DID, claimed with if_absent, and posted Claude’s signed result. Public proof: https://github.com/danenright/technocore-parcel/blob/main/evidence/demo-8c15bda23511955a.json

## Post 5 — 252 characters

The verifier now uses 0.11’s retained sig fields to independently check Ed25519 over room|nonce|text. It binds the task to its creation generation, reads exports around the claim, and rechecks the expected worker pin. Live result: 3/3 signatures valid.

## Post 6 — 241 characters

We proposed the client-side pattern upstream as docs—not a new route or official schema: https://github.com/flop-labs/technocore-chat/pull/162. Independent community work for the agent workflows @flop_labs and @CryptoHayes are inviting; no endorsement or reward guarantee.

## Evidence

- Upgrade and rollback verification: https://github.com/danenright/technocore-deploy/blob/main/evidence/upgrade-0.7.0-to-0.11.4.json
- Capability-free Parcel verification: https://github.com/danenright/technocore-parcel/blob/main/evidence/demo-8c15bda23511955a.json
- Sanitized external Claude result: https://github.com/danenright/technocore-parcel/blob/main/evidence/demo-result-8c15bda23511955a.md
- Upstream documentation proposal: https://github.com/flop-labs/technocore-chat/pull/162
- Official useful-work request: https://x.com/flop_labs/status/2091830155270672521
- Official collaboration statement: https://x.com/CryptoHayes/status/2093281853335535809
