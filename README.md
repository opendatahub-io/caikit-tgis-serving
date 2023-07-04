## Installation

Setting up an OpenShift cluster is outside the scope of this document

1. Set up Istio: [Istio install doc](https://knative.dev/docs/install/installing-istio)
2. Set up KNative Serving: [Knative Serving install doc](https://knative.dev/docs/install/yaml-install/serving/install-serving-with-yaml/)
3. Install Cert Manager: [Cert Manager install doc](https://cert-manager.io/docs/installation/)
4. Install KServe:

```bash
kubectl apply -f https://github.com/kserve/kserve/releases/download/v0.10.0/kserve.yaml
```

## Setting up Caikit

1. Set up servingruntime

The following servingruntime configures caikit

```bash
oc apply -f caikit-servingruntime.yaml
```

Now you have the ability to create inference services for caikit format models

## Converting Model Using Caikit-NLP

Caikit does not have the ability to load generic models, but they can be converted (mostly) from existing HuggingFace models

2. Ensure git/git-lfs is installed

```
yum -y install git git-lfs
git lfs install
```

3. Clone given model (note that the git repo for flan-t5-xl requires roughly 64Gb of storage)

```bash
git clone https://huggingface.co/google/flan-t5-xl
```

- An alternative method that may be a bit smaller of a download

```python
import transformers

pipeline = transformers.pipeline(model="google/flan-tf-xl")

# Model files will be under ~/.cache/huggingface
```

1. Create virtualenv

```bash
python3 -m virtualenv venv
source venv/bin/activate
```

2. Clone caikit-nlp and install

```bash
git clone https://github.com/Xaenalt/caikit-nlp
pip install ./caikit-nlp
```

3. Convert model

```python
import caikit_nlp

base_model_path = "flan-t5-xl"
saved_model_path = "flan-t5-xl-caikit"

# This step imports the model into caikit_nlp and configures in caikit format
model = caikit_nlp.text_generation.TextGeneration.bootstrap(model_path)

# This saves the model out to disk in caikit format. It will consist of a directory with a config.yml and an artifacts directory
model.save(model_path=model_save_path)
```

## Inference with Caikit-Serving

1. Create inferenceservice

```bash
# Edit the yaml to include the storage path of the caikit-format model

oc apply -f caikit-isvc.yaml
```

2. Determine endpoint

```bash
oc get isvc

# Take note of the URL, it will be of the format: isvc-name.project.apps.cluster-name.openshiftapps.com
```

3. Use gRPC to do inference

```bash
# -insecure because the cert is self-signed in this demo environment
# The header mm-model-id is the name of the model loaded in caikit, named the same as the directory the caikit model resides in

grpcurl -insecure -d '{"text": "At what temperature does liquid Nitrogen boil?"}' -H "mm-model-id: flan-t5-xl-caikit" isvc-name.project.apps.cluster-name.openshiftapps.com:443 caikit.runtime.Nlp.NlpService/TextGenerationTaskPredict
```

Output will be similar to (may not be identical, and like sample output may be incorrect):

```json
{
  "generated_token_count": "20",
  "text": " The boiling point of Nitrogen is about -78.0°C, which is the boiling point of",
  "stop_reason": "MAX_TOKENS",
  "producer_id": {
    "name": "Text Generation",
    "version": "0.1.0"
  }
}
```
