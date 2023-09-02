# Accessing Metrics


**Prerequisites**

* Before you begin, complete the prerequisites and install the required operators and components as described in the [Caikit-TGIS-Serving readme file](/docs/README.md).

* Make sure that the `TEST-NS` environment variable is set to the name of your project. For example, if the project name is `kserve-demo`, use this command:
   ~~~
   export TEST_NS=kserve-demo
   ~~~

**Procedure**

1. Navigate to the `/demo/kserve/` directory.

2. Enable and configure User Workload Monitoring.

   ~~~
   oc apply -f custom-manifests/metrics/uwm-cm-enable.yaml -n $TEST_NS
   
   oc apply -f custom-manifests/metrics/uwm-cm-conf.yaml -n $TEST_NS
   ~~~

   Optionally, you can change the retention time by editing the `uwm-cm-conf.yaml` file.

3. Deploy a model by using either of these options:

  - By following step-by-step commands as described in [Deploying an LLM model with the Caikit+TGIS Serving runtime](/docs/deploy-remove.md).   

  - By running scripts as described in [Using scripts to deploy an LLM model with the Caikit+TGIS Serving runtime](deploy-remove-scripts.md).

4. Access Caikit, TGIS and Istio metrics:

   a. From the Openshift Console, select **Observe** --> **Metrics**.

   b. Search for any `caikit_*`, `tgi_*` or `istio_*` metrics.
