# ODH with OSSM enabled

## Prerequisite
- Openshift Cluster 
  - This doc is written based on ROSA cluster
- CLI tools
  - oc cli

- Installed operators
  - [Kiali](https://docs.openshift.com/container-platform/4.13/service_mesh/v2x/installing-ossm.html)
  - [Red Hat OpenShift distributed tracing platform](https://docs.openshift.com/container-platform/4.13/service_mesh/v2x/installing-ossm.html)
  - [Red Hat OpenShift Service Mesh](https://docs.openshift.com/container-platform/4.13/service_mesh/v2x/installing-ossm.html)
    - ServiceMeshControlPlan
  - [OpenDataHub](https://opendatahub.io/docs/quick-installation/)
  - [Authorino](https://github.com/Kuadrant/authorino-operator)

## Reference
- https://github.com/maistra/odh-manifests/blob/ossm_plugin_templates/enabling-ossm.md
- https://github.com/ReToCode/knative-kserve#installation-with-istio--mesh
 
## Setup pre-requisite
~~~
git clone https://github.com/opendatahub-io/caikit-tgis-serving
cd caikit-tgis-serving/demo/kserve

# Install Service Mesh operators
oc apply -f custom-manifests/service-mesh/operators.yaml
sleep 30
oc wait --for=condition=ready pod -l name=istio-operator -n openshift-operators --timeout=300s
oc wait --for=condition=ready pod -l name=jaeger-operator -n openshift-operators --timeout=300s
oc wait --for=condition=ready pod -l name=kiali-operator -n openshift-operators --timeout=300s

# Create an istio instance
oc create ns istio-system
oc create ns opendatahub
oc apply -f custom-manifests/service-mesh/smcp.yaml
oc apply -f custom-manifests/service-mesh/smmr-odh.yaml
oc apply -f custom-manifests/service-mesh/peer-authentication-odh.yaml

sleep 15
oc wait --for=condition=ready pod -l app=istiod -n istio-system --timeout=300s
oc wait --for=condition=ready pod -l app=prometheus -n istio-system --timeout=300s
oc wait --for=condition=ready pod -l app=istio-ingressgateway -n istio-system --timeout=300s
oc wait --for=condition=ready pod -l app=istio-egressgateway -n istio-system --timeout=300s
oc wait --for=condition=ready pod -l app=jaeger -n istio-system --timeout=300s

# Install Authorino/Opendatahub operator
oc create -f custom-manifests/authorino/operators.yaml  
operator-sdk run bundle quay.io/maistra-dev/opendatahub-operator-bundle:v0.0.5-snapshot --namespace openshift-operators --timeout 5m0s

sleep 15
oc wait --for=condition=ready pod -l control-plane=authorino-operator -n openshift-operators --timeout=300s
oc wait --for=condition=ready pod -l control-plane=controller-manager -n openshift-operators --timeout=300s
 
# Deploy opendatahub ossm
oc create ns auth-provider
oc create ns opendatahub
oc create -f custom-manifests/opendatahub/kfdef-plugins.yaml
oc wait --for condition=available kfdef --all --timeout 360s -n opendatahub
oc wait --for condition=ready pod --all --timeout 360s opendatahub
oc get pods -n opendatahub -o yaml | grep -q istio-proxy || oc get deployments -o name -n opendatahub | xargs -I {} oc rollout restart {} -n opendatahub

# Workaround
export TOKEN=$(oc whoami -t)
result=$(oc create -o jsonpath='{.status.audiences[0]}' -f -<<EOF
apiVersion: authentication.k8s.io/v1
kind: TokenReview
spec:
  token: "$TOKEN"
  audiences: []
EOF
)

kubectl patch authconfig odh-dashboard-protection -n opendatahub --type='json' -p="[{'op': 'replace', 'path': '/spec/identity/0/kubernetes/audiences', 'value': ['${result}']}]"
oc adm policy add-cluster-role-to-user cluster-admin joe

export ODH_ROUTE=$(oc get route --all-namespaces -l maistra.io/gateway-namespace=opendatahub -o yaml | yq '.items[].spec.host')
xdg-open https://$ODH_ROUTE > /dev/null 2>&1 &    


# Customize ossm
 oc scale deploy/opendatahub-operator-controller-manager -n openshift-operators --replicas=0

~~~

## Troubleshooting
`OAuth flow failed`
~~~
kubectl logs $(kubectl get pod -l app=oauth-openshift -n openshift-authentication -o name|head -n1) -n openshift-authentication  

kubectl get oauthclient.oauth.openshift.io opendatahub-oauth2-client
kubectl exec $(kubectl get pods -n istio-system -l app=istio-ingressgateway  -o jsonpath='{.items[*].metadata.name}') -n istio-system -c istio-proxy -- cat /etc/istio/opendatahub-oauth2-tokens/token-secret.yaml
kubectl get secret opendatahub-oauth2-tokens -n istio-system -o yaml

kubectl rollout restart deployment -n istio-system istio-ingressgateway 

oc create -o yaml -f -<<EOF
apiVersion: authentication.k8s.io/v1
kind: TokenReview
spec:
  token: "$TOKEN"
  audiences: []
EOF
~~~
