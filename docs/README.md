# Caikit-TGIS-Serving

Caikit-tgis-serving is a combined image that allows users to perform LLM inference.

It consists of several components:
* **[TGIS](https://github.com/opendatahub-io/text-generation-inference)**: Serving backend, loads the models, and provides the inference engine
* **[Caikit](https://github.com/opendatahub-io/caikit)**: Wrapper layer that handles the lifecycle of the TGIS process, provides the inference endpoints, and has modules to handle different model types
* **[Caikit-nlp](https://github.com/opendatahub-io/caikit-nlp)**: Caikit module that handles NLP style models
* **[KServe](https://github.com/opendatahub-io/kserve)**: Orchestrates model serving for all types of models, servingruntimes implement loading given types of model servers. KServe handles the lifecycle of the deployment object, storage access, networking setup, etc.
* **[Service Mesh](https://docs.openshift.com/container-platform/4.13/service_mesh/v2x/ossm-architecture.html)** (istio): Service mesh networking layer, manages traffic flows, enforces access policies, etc.
* **[Serverless](https://docs.openshift.com/serverless/1.29/about/about-serverless.html)** (knative): Allows for serverless deployments of models


## Installation
### Prerequisites
- Openshift Cluster 
  - This doc is written based on a ROSA cluster and has been tested with an OSD cluster as well
  - Many of the tasks in this tutorial require cluster-admin permission level (e.g., install operators, set service-mesh configuration, enable http2, etc)
  - 4 CPU and 16 GB memory in a node for inferencing (can be adjusted in servingRuntime deployment)
- CLI tools
  - oc cli


### How to install

The following required operators will be installed as part of the KServe/Caikit/TGIS stack installation instructions.
- [Kiali](https://docs.openshift.com/container-platform/4.13/service_mesh/v2x/installing-ossm.html)
- [Red Hat OpenShift distributed tracing platform](https://docs.openshift.com/container-platform/4.13/service_mesh/v2x/installing-ossm.html)
- [Red Hat OpenShift Service Mesh](https://docs.openshift.com/container-platform/4.13/service_mesh/v2x/installing-ossm.html)
  - ServiceMeshControlPlan
- [Openshift Serverless](https://docs.openshift.com/serverless/1.29/install/install-serverless-operator.html)
- [OpenDataHub](https://opendatahub.io/docs/quick-installation/)

There are three ways to install the KServe/Caikit/TGIS stack (includes the installation of above-mentioned required operators).
1. [Script-based installation](/demo/kserve/scripts/README.md)
2. [Manual installation](/demo/kserve/install-manual.md)

## Demos with LLM model
- [Deploy a model and remove/undeploy a model](/docs/deploy-remove.md)
- [Split traffic](/docs/traffic-splitting.md)
- [Upgrade runtime](/docs/upgrade-runtime.md)
- [Access metrics](/docs/metrics.md)

## Architecture of the stack

![KServe+Knative+Istio+Caikit_TGIS Diagram](https://github.com/opendatahub-io/caikit-tgis-serving/assets/8479010/7009b95d-0f6f-4f18-b0e6-355f360a5ad1)
