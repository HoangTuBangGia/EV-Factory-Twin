# Branch-Isolated GCP CI/CD

## Summary

Added keyless, CI-gated continuous delivery for `develop` and `main`, with
separate Cloud Run services, deploy identities, runtime identities, secrets,
and Cloud SQL instances.

## Motivation

Manual build and deployment proved the GCP stack, but repeating operator
commands after every merge is slow and makes commit-to-revision traceability
easy to lose. Develop automation must not overwrite or mutate production.

## Architecture / Contract Impact

The CI workflow invokes branch-specific wrappers only after all required jobs
pass. Google Cloud authentication uses separate branch- and repository-scoped
Workload Identity providers. Images use the full reviewed Git SHA, and each
service allows only its matching Vercel origin.

An operator bootstraps the service's public invoker policy once. Automation has
Cloud Run Developer permission and cannot alter that policy. Artifact Registry
write access is scoped to the existing `ev-twin` repository.

PostgreSQL DDL remains operator-controlled. A commit that changes migrations is
blocked until the operator applies the ledger-backed migrations and manually
confirms that action. ROS/Gazebo VM deployment remains outside this workflow
until a least-privilege, approval-gated edge deployment identity exists.

Production ROS/Gazebo now has a separately provisioned private Compute Engine
VM. Cloud NAT provides outbound-only access, and an idempotent IAP bootstrap
installs ROS 2 Jazzy with its supported Gazebo Harmonic pairing without checking
out application code or materializing secrets.

## Files Changed

- `.github/workflows/deploy-gcp.yml`
- `.github/workflows/deploy-gcp-develop.yml`
- `.github/workflows/deploy-gcp-production.yml`
- `.github/workflows/ci.yml`
- `.gitignore`
- `.dockerignore`
- `Makefile`
- `scripts/gcp_edge_bootstrap.sh`
- `tests/integration/test_gcp_develop_cicd.py`
- `docs/deployment.md`
- `docs/runbooks/gcp-operations.md`
- `docs/changes/m14-4-develop-cicd.md`

## Verification

- `make gcp-backend-check`: migration contracts and 11 GCP deployment contract
  tests passed.
- `make check`: Ruff, formatting, Mypy, and 406 Python tests passed; 2 hosted
  PostgreSQL repository smoke tests skipped because `TEST_DATABASE_URL` was not
  configured.
- `make frontend-check`: ESLint, TypeScript, 107 Vitest tests, and the Next.js
  production build passed.

## CI / Build Impact

Existing PR CI is unchanged. After merge, a successful push CI invokes the
matching branch deployment. Per-environment concurrency locks serialize
deployments without cancelling an active rollout.

## Follow-up

Finish both GitHub Environments, provision and migrate production Cloud SQL,
bootstrap both public Cloud Run services, and complete branch-specific hosted
acceptance. Install the accepted production commit and environment-specific
bridge configuration on the production edge VM. Add approval-gated ROS VM
delivery only after installing a restricted deployment wrapper on each VM.
