Docs for setting up a demo cluster can be found ![here](https://github.com/opendatahub-io/caikit-tgis-serving/tree/main/demo/kserve)

Caikit-tgis-serving is a combined image that allows users to perform LLM inference.

The architecture is shown here:

![KServe+Knative+Istio+Caikit_TGIS Diagram](https://github.com/opendatahub-io/caikit-tgis-serving/assets/8479010/7009b95d-0f6f-4f18-b0e6-355f360a5ad1)

There are several components:
* **TGIS**: Serving backend, loads the models, and provides the inference engine
* **Caikit**: Wrapper layer that handles the lifecycle of the TGIS process, provides the inference endpoints, and has modules to handle different model types
* **Caikit-nlp**: Caikit module that handles NLP style models
* **KServe**: Orchestrates model serving for all types of models, servingruntimes implement loading given types of model servers. KServe handles the lifecycle of the deployment object, storage access, networking setup, etc
* **Service Mesh** (istio): Service mesh networking layer, manages traffic flows, enforces access policies, etc
* **Serverless** (knative): Allows for serverless deployments of models
