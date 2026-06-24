# run

To activate the Python virtual environment in this workspace, run:
```
source .venv/bin/activate
```

# Usage History

## marketplace
```bash
python az-vars.py --project marketplace-accounting --group backend-prod --set OtelEnvironment=PROD
python az-vars.py --project marketplace-accounting --group backend-prod --set OtelEndpoint=http://alloy-central.alloy-prod-internal:14317

python az-vars.py --project marketplace-accounting --group backend-uat --set OtelEnvironment=UAT
python az-vars.py --project marketplace-accounting --group backend-uat --set OtelEndpoint=http://alloy-central.alloy-test-internal:14317
```

```bash
python az-vars.py --group anna-api-dev --set OtelEnvironment=DEV
python az-vars.py --group anna-api-dev --set OtelEndpoint=http://alloy-central.alloy-test-internal:14317 

python az-vars.py --group anna-api-uat --set OtelEnvironment=UAT
python az-vars.py --group anna-api-uat --set OtelEndpoint=http://alloy-central.alloy-test-internal:14317 

python az-vars.py --group anna-api-prod --set OtelEnvironment=PROD
python az-vars.py --group anna-api-prod --set OtelEndpoint=http://alloy-central.alloy-prod-internal:14317

python az-vars.py --group _removed_annaproxy-api-grafana-dev-vars
  Variable Group: _removed_annaproxy-api-grafana-dev-vars  (id=141)

  Variable                                 Value
  ----------------------------------------------------------------------
  GrafanaLogsApikey                        ****** (secret)
  GrafanaLogsEndpoint                      https://logs-prod-012.grafana.net/loki/api/v1/push
  GrafanaLogsUser                          468788
  GrafanaMetricsApikey                     ****** (secret)
  GrafanaMetricsEndpoint                   https://prometheus-prod-24-prod-eu-west-2.grafana.net/api/prom/push
  GrafanaMetricsUser                       939639
  GrafanaTracesApikey                      ****** (secret)
  GrafanaTracesEndpoint                    tempo-prod-10-prod-eu-west-2.grafana.net:443
  GrafanaTracesUser                        465302

python az-vars.py --group _removed_annaproxy-api-grafana-dev-vars --delete GrafanaLogsUser
```