# Task 3 / Part C — promote v6 via the CLI

Using the promotion CLI built in Task 2 to move the `production` alias from v4 to v6. The follow-up `show` confirms the alias now resolves to v6 (MLflow version 5) and surfaces the v6 metrics.

```
(.venv) dgwalters@boomer mlops-hw-2 % python scripts/promo
te.py set production v6
production: v4 → v6

(.venv) dgwalters@boomer mlops-hw-2 % python scripts/promote.py show production 
travel-assistant @ production
  model_version: 5
  config_id: v6
  model: nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B
  accuracy_overall: 0.97
  verdict_rate_leaked: 0.01
  total_cost_usd: $0.03
```
