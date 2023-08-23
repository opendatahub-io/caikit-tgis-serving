# Traffic Splitting
In this example, we will be splitting traffic 80:20 between two inference services.

Before proceding, please ensure you have [installed](/docs/README.md) all pre-requisites, required operators and components, and you have [deployed a model](/docs/deploy-remove.md)
## Setting up the inference services
Deploy a second inference service 
~~~
oc apply -f ./custom-manifests/caikit/caikit-isvc-2.yaml -n ${TEST_NS}
~~~
Check that the `READY` field of both inference services is set to `True`:
~~~
oc get isvc -n ${TEST_NS}
~~~
Add the following annotations to your namespace to configure the Istio Gateway to use to expose the Inference Services created the namespace:
~~~
oc annotate ns ${TEST_NS} service-mesh.opendatahub.io/public-gateway-name=gateway-namespace-name/gateway-resource-name
oc annotate ns ${TEST_NS} service-mesh.opendatahub.io/public-gateway-host-internal=in-cluster-gateway.namespace.svc.cluster.local
~~~

## Configuring the traffic splitting
In order to perform traffic splitting, inference services need to be grouped. We will create a caikit-group.
~~~
ISVC_GROUP_NAME=caikit-group
oc label isvc caikit-example-isvc serving.kserve.io/model-tag=$ISVC_GROUP_NAME
oc label isvc caikit-example-isvc-2 serving.kserve.io/model-tag=$ISVC_GROUP_NAME
~~~
We will then label the inference services with the desired percentages. `caikit-example-isvc` will receive 80% of the traffic and `caikit-example-isvc-2` will receive 20% of the traffic.
~~~
oc annotate isvc caikit-example-isvc serving.kserve.io/canaryTrafficPercent=80
oc annotate isvc caikit-example-isvc-2 serving.kserve.io/canaryTrafficPercent=20
~~~

## Perform Inference with gRPC calls
In order to make a gRPC call, check if HTTP2 protocol is enabled in the cluster.
~~~
oc get ingresses.config/cluster -ojson | grep ingress.operator.openshift.io/default-enable-http2
~~~

If the annotation is either set to false or not present, enable it:
~~~
oc annotate ingresses.config/cluster ingress.operator.openshift.io/default-enable-http2=true
~~~

You can run the following grpcurl command for all tokens in a single call:
~~~
export KSVC_HOSTNAME=$(oc get ksvc caikit-example-isvc-predictor -n ${TEST_NS} -o jsonpath='{.status.url}' | cut -d'/' -f3)
grpcurl -insecure -d '{"text": "At what temperature does liquid Nitrogen boil?"}' -H "mm-vmodel-id: $ISVC_GROUP_NAME" ${KSVC_HOSTNAME}:443 caikit.runtime.Nlp.NlpService/TextGenerationTaskPredict
~~~
The expected response should be similar to:
~~~
{
  "generated_token_count": "5",
  "text": "74 degrees F",
  "stop_reason": "EOS_TOKEN",
  "producer_id": {
    "name": "Text Generation",
    "version": "0.1.0"
  }
}
~~~