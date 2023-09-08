# Performance configuration for Caikit+TGIS ServingRuntime


**Continuous Batching**

There are a few relevant configuration settings to control how TGIS does continuous batching of incoming requests.

1. gRPC server thread pool size:
   
   The first important setting to enable batching is to increase the gRPC server thread pool size which is by default 5. This will limit the number of concurrent requests that can be processed, which in turn limits batch sizes.
   
   This can be increased by setting the `RUNTIME_GRPC_SERVER_THREAD_POOL_SIZE` environment variable in the ServingRuntime yaml: 
   
   ~~~
   ...
   spec:
     containers:
     - name: kserve-container
   ...
       env:
       - name: RUNTIME_GRPC_SERVER_THREAD_POOL_SIZE
         value: "64"
   ~~~
   
   This will be an upper-bound for the batch sizes that are possible.
   
2. Max batch size and batch weight:
   
   Other settings needed to enable large batch sizes include `MAX_BATCH_SIZE`, `MAX_CONCURRENT_REQUESTS`, and `MAX_BATCH_WEIGHT`. These can also be set via environment variables in the ServingRuntime.
   
   As an example, from the ServingRuntime used in performance testing of gpt-neox-20b:
   
   ~~~
   ...
   spec:
     containers:
     - name: kserve-container
   ...
       env:
       - name: RUNTIME_GRPC_SERVER_THREAD_POOL_SIZE
         value: "256"
       - name: MAX_BATCH_SIZE
         value: "256"
       - name: MAX_CONCURRENT_REQUESTS
         value: "64"
       - name: MAX_BATCH_WEIGHT
         value: "10000"
   ~~~
   
   `MAX_BATCH_SIZE` is an upper-bound of batch size. The `MAX_BATCH_WEIGHT` is a separate bound on how large batches can be, which requires some tuning. The batch weight for LLMs like gpt-neox-20b is calculated as batch_size * seq_length^2, and TGIS will fit requests into a batch to keep that value below MAX_BATCH_WEIGHT.  
   
   


**PyTorch 2 Compilation**

Some models can be optimized by compiling some functions into optimized kernels using the PT2_COMPILE environment variable. This can offer a good speedup, but it comes at the cost of a longer model-load/warmup phase which can take 20+ minutes depending on the model. By default model loading times out after 2 minutes. This 2 minute timeout can be increased by overriding a setting in the caikit-tgis.yml in the container, using a ConfigMap.

See the below example from the flan-t5-large ServingRuntime YAML manifest used in the PSAP teams testing:
~~~
...
spec:
  containers:
  - name: kserve-container
...
    env:
    - name: PT2_COMPILE
      value: "true"
...
    volumeMounts:
    - name: runtime-config
      subPath: runtime_config.yaml
      mountPath: "/caikit/config/caikit-tgis.yml"
...
  volumes:
    - name: runtime-config
      configMap:
        name: runtime-config
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: runtime-config
data:
  caikit-tgis.yml: |
    jvm_options: []
...
    model_management:
      initializers:
        default:
          type: LOCAL
          config:
            backend_priority:
              - type: TGIS
                config:
                  local:
                    load_timeout: 2000
...
~~~

This load_timeout setting increases the timeout to over 30 minutes.


