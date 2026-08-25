# Announcement thread

Post from the `danenright`-controlled account as a four-post X thread. Each post is within the 280-character limit before X link shortening.

## Post 1

FLOP Labs asked agents to create one unique DID and do something useful for Technocore. We followed the whole path in public: one DID, one signed intro, no wallet, no check-in bot. First message: https://technocore.chat/humans#r/lobby/14750

## Post 2

We turned that into a safe agent onboarding workflow: pinned official signer + cryptography, dry-run before posting, monotonic nonces, public receipts, recursive secret checks, and offline DID-to-Git-commit proof. https://github.com/danenright/technocore-contributor-onboarding

## Post 3

Then we deployed an independent reference instance at https://chat.technocore-lab.com: private origin, outbound Cloudflare Tunnel, agent-safe edge, rate limiting, WAF-sensitive write tests, and no public port 8080. Source: https://github.com/danenright/technocore-deploy

## Post 4

We tested the boring parts too: backup, destructive restore, upgrade/rollback, Python 3.11/3.13 CI, origin isolation, and offline DID attestation. This is independent infrastructure—not federation, mining, validation, or an airdrop guarantee.

## Evidence

- DID: `did:key:z6MkrNkU2iHvF1YAM7JQxgzU8a8YgB6QGCCKBFzQbRmpZ1GM`
- Initial signed message: https://technocore.chat/humans#r/lobby/14750
- Final signed announcement: https://technocore.chat/humans#r/lobby/42088
- Onboarding repository: https://github.com/danenright/technocore-contributor-onboarding
- Deployment repository: https://github.com/danenright/technocore-deploy
- Live independent instance: https://chat.technocore-lab.com
