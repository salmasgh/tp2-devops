# TP2 DevOps Avancé — Payment API

Continuous Delivery, Quality & Security Gates, et Ingénierie SRE avec Observabilité Cloud-Native.

| Dossier | Contenu |
|---|---|
| `app/` | Microservice FastAPI (`/products`, `/payments`, `/checkout` lent, `/flaky` erreurs intermittentes, `/metrics`) instrumenté OpenTelemetry |
| `tests/` | Tests unitaires/intégration pytest (couverture ≥ 85 %, rapports Cobertura `coverage.xml` + LCOV) |
| `Dockerfile` | Image multi-stage non-root |
| `.github/workflows/ci.yml` | Lint & Test → SonarQube Quality Gate → Build → Trivy (CRITICAL = fail) → Push GHCR → bump GitOps |
| `ci/sonar-setup.sh` | Configuration de la Quality Gate stricte SonarQube |
| `policies/` | ConstraintTemplates OPA Gatekeeper (Rego) + manifestes de test |
| `k8s/` | Manifestes Kustomize (base + overlay dev) |
| `argocd/` | Application ArgoCD (GitOps) |
| `observability/` | Valeurs Helm Prometheus / Grafana / Loki / Tempo / OTel Collector, dashboard SRE, règles d'alerte burn-rate |
| `k6/` | Script de charge k6 (ramp-up 100 VU, stress 500 VU, spike 1500 VU) |
