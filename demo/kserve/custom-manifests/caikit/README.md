# Caikit serving

This directory includes [InferenceService](https://kserve.github.io/website/latest/reference/api/#serving.kserve.io/v1beta1.InferenceService) and [ServingRuntime](https://kserve.github.io/website/latest/reference/api/#serving.kserve.io/v1alpha1.ServingRuntime) definitions for language model serving using [caikit](https://github.com/caikit/caikit) and [caikit-nlp](https://github.com/caikit/caikit-nlp).

- [caikit-standalone](./caikit-standalone): caikit-only solution
- [caikit-tgis](./caikit-tgis): caikit frontend with a [text-generation-inference](https://github.com/IBM/text-generation-inference) (tgis) backend solution. See [tgis](../tgis/) for a tgis-only solution.
