# Access Metrics
Before proceding, please ensure you have [installed](/docs/README.md) all pre-requisites, required operators and components

## Setup

To access the metrics, let's enable and configure the User Workload Monitoring.
~~~
oc apply -f uwm-cm-enable.yaml -n $TEST_NS
oc apply -f uwm-cm-conf.yaml-n $TEST_NS
~~~
If desired, the retention time can be changed in `uwm-cm-conf.yaml`.

## Deploy a model

Please deploy a model following instructions [here](/docs/deploy-remove.md).

## Accessing Caikit, TGIS and Istio metrics

Navigate to Openshift Console --> Observe --> Metrics.

Search for any `caikit_*`, `tgi_*` or `istio_*` metrics.

Available metrics are:
~~~
//TODO: add list of metrics here
~~~
