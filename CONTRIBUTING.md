# Contributing

## Branch Strategy

- `main`: stable/demo/production
- `develop`: integration
- `feat/*`: new features
- `fix/*`: bug fixes
- `docs/*`: documentation
- `test/*`: testing
- `chore/*`: tooling and infrastructure

Do not push directly to `main` or `develop`.

## Development Workflow

```bash
git switch develop
git pull --ff-only
git switch -c feat/my-feature
```

## Before opening a pull request:

```bash
make check

# Then:
git push -u origin feat/my-feature
```

## Open the pull request against develop.

## Releases
Release pull requests go from:
develop -> main