# Phoenix — Intentionally Vulnerable Flask App

[![CI](https://github.com/anshumaan-10/phoenix/actions/workflows/build-push.yaml/badge.svg)](https://github.com/anshumaan-10/phoenix/actions/workflows/build-push.yaml)
[![Docker Hub](https://img.shields.io/docker/v/anshumaan10/phoenix?label=Docker%20Hub)](https://hub.docker.com/r/anshumaan10/phoenix)

Part of the [k8s-security-lab](https://github.com/anshumaan-10/k8s-security-lab) — a hands-on Kubernetes security research environment.

> **Warning:** This application is **intentionally vulnerable**. It contains a remote code execution endpoint. Do not deploy to any real environment.

---

## What Is This

Phoenix is a Flask web service with:
- A normal dashboard (`/`) showing service status
- A **hidden RCE debug endpoint** (`/$DEBUG_PATH/`) that executes arbitrary shell commands as `root`

The RCE endpoint is enabled by setting the `DEBUG_PATH` environment variable. Combined with a privileged Kubernetes pod spec (`hostPID`, `hostNetwork`, `hostPath:/`), this allows full host node escape — see [VULN-01](https://github.com/anshumaan-10/k8s-security-lab/tree/main/vulnerabilities/VULN-01-privileged-pod).

---

## Quick Start

```bash
# Run locally
docker run -p 8080:8080 -e DEBUG_PATH=debug anshumaan10/phoenix:latest

# Dashboard
curl http://localhost:8080/

# RCE endpoint (POST cmd=<shell command>)
curl -s -X POST http://localhost:8080/debug/ -d 'cmd=id'
# uid=0(root) gid=0(root) groups=0(root)
```

Or with Docker Compose from the main lab:

```bash
git clone https://github.com/anshumaan-10/k8s-security-lab
cd k8s-security-lab
docker compose up
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DEBUG_PATH` | _(unset)_ | Path segment for RCE endpoint; if unset, endpoint is disabled |
| `DEPLOYMENT_NAME` | `phoenix-app` | Label shown in dashboard |
| `PAYMENT_API_URL` | `http://payment-api:8080/health` | URL checked for payment-api status |
| `NODE_NAME` | _(unset)_ | Injected by Kubernetes downward API |
| `POD_IP` | _(unset)_ | Injected by Kubernetes downward API |
| `NAMESPACE` | _(unset)_ | Injected by Kubernetes downward API |

---

## Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Dashboard — service status |
| `GET` | `/health` | Health check — returns `{"status":"ok"}` |
| `GET/POST` | `/$DEBUG_PATH/` | **RCE console** (only if `DEBUG_PATH` is set) |

---

## CI/CD

On every push to `main`, GitHub Actions:
1. Builds `linux/amd64` image
2. Pushes `anshumaan10/phoenix:<commit-sha>` and `anshumaan10/phoenix:latest` to Docker Hub
3. Updates `deployments/phoenix/deployment.yaml` in [k8s-lab-deployments](https://github.com/anshumaan-10/k8s-lab-deployments) with the new SHA tag

**Required GitHub Secrets** (set in repo Settings → Secrets):

| Secret | Value |
|---|---|
| `DOCKERHUB_USERNAME` | `anshumaan10` |
| `DOCKERHUB_TOKEN` | Docker Hub access token |
| `DEPLOY_PAT` | GitHub PAT with `repo` scope for updating k8s-lab-deployments |

---

## Security Notes (for the Lab)

The vulnerability demonstrated:

| VULN | Description |
|---|---|
| [VULN-01](https://github.com/anshumaan-10/k8s-security-lab/tree/main/vulnerabilities/VULN-01-privileged-pod) | RCE via `/$DEBUG_PATH/` + privileged pod = full host escape |

The fix is **not** to remove the debug endpoint from the app — it is to:
1. Remove `privileged: true`, `hostPID`, `hostNetwork`, `hostPath:/` from the pod spec
2. Add Pod Security Admission (`restricted` profile)
3. Run as non-root user
