# Bootstrap process (optional)

Caikit requires equires a Caikit-formatted model. Below are the instructions from converting a model to a Caikit-formatted one.

1. Clone the model repository (or have the model folder in a directory). In the below example, Bloom-560m model repo is cloned.

```bash
yum -y install git git-lfs
git lfs install
git clone https://huggingface.co/bigscience/bloom-560m
```

2. Create a virtual environment with Python 3.9 and install `caikit-nlp`

```bash
python3 -m venv -p python3.9 venv
source venv/bin/activate
python3.9 -m pip install git+https://github.com/caikit/caikit-nlp.git
```

3. (Optional) Clone the `caikit-tgis-serving` repo, if not already available.

```bash
git clone https://github.com/opendatahub-io/caikit-tgis-serving.git
```

4. Invoke the conversion script located in /utils of caikit-tgis-serving repo.

```bash
caikit-tgis-serving/utils/convert.py --model-path ./bloom-560m/ --model-save-path ./bloom-560m-caikit
```

5. Move the model folder (ie. `/bloom-560m-caikit`) into desired storage (ie. S3, MinIO, PVC or other)
6. Do **not** include the model folder name/directory directly in `InferenceService`, but rather point to the directory where the model folder is located. Let's say the `bloom-560m-caikit` directory is located at: `example-models/llm/models/bloom-560m-caikit/`, then `storageUri` value in the InferenceService CR should look like:

```bash
storageUri: s3://example-models/llm/models
```
