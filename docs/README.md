# Caikit-TGIS-Serving

Caikit-TGIS-Serving is a stack that allows data scientists to perform Large Language Model (LLM) inference.

The Caikit-TGIS-Serving stack consists of these components:

- **[Caikit](https://github.com/opendatahub-io/caikit)**: Caikit is an AI toolkit that enables users to manage models through a set of developer friendly APIs.
- **[Caikit-nlp](https://github.com/opendatahub-io/caikit-nlp)**: Caikit module that handles Natural Language Processing (NLP) models and tasks.
- **[Text Generation Inference Server (TGIS)](https://github.com/opendatahub-io/text-generation-inference)**: Runtime that loads the models and provides the inference engine.
- **[KServe](https://github.com/opendatahub-io/kserve)**: A Kubernetes Custom Resource Definition that orchestrates model serving for all types of models. It includes serving runtimes that implement the loading of given types of model servers. KServe handles the lifecycle of the deployment object, storage access, and networking setup.
- **[Service Mesh](https://docs.openshift.com/container-platform/4.13/service_mesh/v2x/ossm-architecture.html)** (istio): The service mesh networking layer that manages traffic flows and enforces access policies.
- **[Serverless](https://docs.openshift.com/serverless/1.29/about/about-serverless.html)** (knative): A cloud-native development model that allows for serverless deployments of data models.

## Architecture of the stack

![KServe+Knative+Istio+Caikit_TGIS Diagram](https://github.com/opendatahub-io/caikit-tgis-serving/assets/8479010/7009b95d-0f6f-4f18-b0e6-355f360a5ad1)

## Installation

The procedures for installing and deploying the Caikit-TGIS-Serving stack have been tested with Red Hat OpenShift Data Science self-managed on Red Hat OpenShift Service for AWS (ROSA) and OpenShift Dedicated clusters. They have not been tested with the OpenShift Data Science managed cloud service.

### Prerequisites

- To support inferencing, your cluster needs a node with 4 CPUs and 8 GB memory. You can adjust these settings in the `spec.resources.requests` section of the Serving Runtime custom resource.
- You need cluster administrator permissions for many of the procedures (such as, installing operators, setting service-mesh configuration, and enabling http2).
- You have installed the OpenShift CLI (`oc`).

### Procedures

As of Red Hat OpenShift Data Science version 2.5.0, you can follow the official docs [here](https://access.redhat.com/documentation/en-us/red_hat_openshift_ai_self-managed/2.5/html/working_on_data_science_projects/serving-large-language-models_serving-large-language-models) for up-to-date installation instructions.

For RHODS<2.5.0 and ODH, there are two ways to install the KServe/Caikit/TGIS stack:

- [Step-by-step command installation](/demo/kserve/install-manual.md)
- [Script-based installation](/demo/kserve/scripts/README.md)

  Note: The installation procedures include commands for installing the following operators, which are required by the KServe/Caikit/TGIS stack:

  - [Red Hat OpenShift Service Mesh](https://docs.openshift.com/container-platform/4.13/service_mesh/v2x/installing-ossm.html)
  - [OpenShift Serverless](https://docs.openshift.com/serverless/1.29/install/install-serverless-operator.html)
  - [Open Data Hub](https://opendatahub.io/docs/quick-installation/)

## Demos

After you install the KServe/Caikit/TGIS stack, you can try these demos:

- Deploying and removing a model [by using step-by-step commands](/demo/kserve/deploy-remove.md) or [by running scripts](/demo/kserve/deploy-remove-scripts.md)
- [Splitting traffic](/demo/kserve/traffic-splitting.md)
- [Upgrading the runtime](/demo/kserve/upgrade-runtime.md)
- [Accessing metrics](/demo/kserve/metrics.md)
- [Performance Configuration](/demo/kserve/performance-config.md)
