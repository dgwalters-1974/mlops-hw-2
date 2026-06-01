# Task 3 / Part D — hot reload to pick up v6

The service was restarted with `ASSISTANT_MODEL_ALIAS=production` (production mode) and resolved the alias to v6 on startup. Hitting `/admin/reload` re-resolves the alias atomically — both `previous` and `current` show v6 with `model_alias: "production"` and `model_version: "5"`, confirming the live pipeline is the sandwich/hardened prompt v6 we just promoted.

```
(.venv) dgwalters@boomer mlops-hw-2 % curl -X POST http://localhost:8000/admin/reload
{"status":"ok","previous":{"config_id":"v6","model":"nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B","guardrail_type":"sandwich","model_name":"travel-assistant","model_alias":"production","model_version":"5"},"current":{"config_id":"v6","model":"nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B","guardrail_type":"sandwich","model_name":"travel-assistant","model_alias":"production","model_version":"5"}}% 
```
