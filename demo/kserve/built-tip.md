# Bootstrap process

Caikit requires requires a Caikit-formatted model which can be converted from a Hugging Face model using the [caikit-nlp](https://github.com/opendatahub-io/caikit-nlp) module.

## Converting Hugging Face Hub models to Caikit Format

1. Create a virtual environment with Python 3.9 and install `caikit-nlp`:

```bash
python3.9 -m venv venv
source ./venv/bin/activate
pip install caikit-nlp
```

2. If the model has not already been downloaded, setting the environment variable `ALLOW_DOWNLOADS=1` will allow direct downloads of models from Hugging Face Hub:

```bash
export ALLOW_DOWNLOADS=1
```

Run the following python snippet.

```python
import caikit_nlp

model_name="google/flan-t5-small" # modify as required
converted_model_path=f"{model_name}-caikit"

caikit_nlp.text_generation.TextGeneration.bootstrap(model_name).save(converted_model_path)
print(f"Model saved to {converted_model_path}")
```

Note: If the model has already been downloaded locally, it will be sufficient to change `model_name` with the path to the model.

## Serving the model

1. Move the converted model folder (ie. `/bloom-560m-caikit`) into desired storage (ie. S3, MinIO, PVC or other)

2. Edit the `InferenceService` manifest so that it points to the desidered storage.
   Do **not** include the model folder name/directory directly in `InferenceService`, but rather point to the directory where the model folder is located. Let's say the `bloom-560m-caikit` directory is located at: `example-models/llm/models/bloom-560m-caikit/`, then `storageUri` value in the InferenceService CR should look like:

   ```yaml
   storageUri: s3://example-models/llm/models
   ```
