# Runbook — payment-api : Error Budget burn

## Alertes
| Alerte | Condition | Canal |
|---|---|---|
| `PaymentApiErrorBudgetBurnCritical` | burn rate 1h > 14.4 **et** 5m > 14.4 (2 % du budget mensuel en 1 h) | pager |
| `PaymentApiErrorBudgetBurnWarning` | burn rate 6h > 6 **et** 30m > 6 (5 % du budget mensuel en 6 h) | Slack `#sre-alerts` |
| `PaymentApiLatencySLOBreach` | p95 (5m) > 200 ms | Slack |

SLO disponibilité : 99.5 % (error budget 0.5 %). SLO latence : p95 ≤ 200 ms.

## Diagnostic
1. Grafana → dashboard **Payment API - SRE** : quelle route produit les 5xx (panneau *Errors*) ? depuis quand (panneau *Burn Rate*) ?
2. Corréler avec un déploiement : ArgoCD → `payment-api` → *History and Rollback* ; `git log k8s/`.
3. Panneau *Logs* (Loki) : `{service_name="payment-api"} | json | level="ERROR"` → cliquer le `trace_id` pour ouvrir la trace Tempo.

## Remédiation
- Release fautive : `git revert <commit>` puis push sur `main` → ArgoCD resynchronise automatiquement (Git reste la source de vérité ; un rollback depuis l'UI ArgoCD serait écrasé par l'auto-sync).
- Saturation (latence) : augmenter `replicas` dans `k8s/overlays/dev/kustomization.yaml` ou les `limits` CPU.

## Clôture
Vérifier que `slo:burn_rate:5m` repasse sous 1, puis rédiger le post-mortem (impact = budget consommé, panneau *Error Budget Remaining*).
