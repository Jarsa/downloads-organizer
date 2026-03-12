# PyPI Trusted Publishing Setup

This project uses **PyPI Trusted Publishing (OIDC)** — no API tokens required.

## Steps

### 1. Create a PyPI account

Go to <https://pypi.org> and register.

### 2. Add a Pending Publisher

1. Log in to PyPI.
2. Go to your account → **Publishing** → **Add a new pending publisher**.
3. Fill in:

   | Field | Value |
   |-------|-------|
   | PyPI project name | `downloads-organizer` |
   | Owner (GitHub username/org) | `jarsa` |
   | Repository name | `downloads-organizer` |
   | Workflow filename | `release.yml` |
   | Environment name | `pypi` |

4. Click **Add**.

### 3. Create a GitHub Environment

1. Go to the repository → **Settings** → **Environments** → **New environment**.
2. Name it `pypi`.
3. Optionally add protection rules (e.g., require a review before publishing).

### 4. Trigger a Release

Create and push a version tag:

```bash
git tag v1.0.0
git push origin v1.0.0
```

The `release.yml` workflow will:
1. Build the wheel and source distribution.
2. Publish to PyPI via OIDC (no secrets needed).
3. Create a GitHub Release with the CHANGELOG notes.

### Notes

- No `PYPI_API_TOKEN` secret is needed — OIDC handles authentication automatically.
- The environment name in the workflow (`pypi`) must match the environment created in step 3.
- First-time publishing uses the "pending publisher" configured in step 2; subsequent releases use the existing PyPI project.
