# How to use install 

**Git clone**
~~~
git clone https://github.com/opendatahub-io/caikit-tgis-serving
cd caikit-tgis-serving/demo/kserve
~~~

(NOTE) If you want to use brew, please do pre-requisites before you use this script.
- Create a credential secret
- Create ICSP

**Set environment variable(Optional)**

If below variables are not set, the script will ask it. 

- Brew
~~~
export TARGET_OPERATOR=brew
export BREW_TAG=554169
~~~

- RHODS (1.32+)
~~~
export TARGET_OPERATOR=rhods
~~~

- ODH (1.9+)
~~~
export TARGET_OPERATOR=odh
~~~

*Variables description*
- CHECK_UWM: Set this to "false", if you want to skip the User Workload Configmap check message
- TARGET_OPERATOR: Set this among odh, rhods or brew, if you want to skip the question in the script.
- BREW_TAG: Set this, when you want to choose brew for TARGET_OPERATOR.
- CUSTOM_MANIFESTS_URL: Set this, when you want to use custom manifests(ex, https://github.com/opendatahub-io/odh-manifests/tarball/master)
  

**Install Kserve including dependencies**

~~~
./scripts/install/kserve-install.sh
~~~

**Deploy a sample model**

~~~
./scripts/test/deploy-model.sh
~~~

**gRPC test**
~~~
./scripts/test/grpc-call.sh
~~~

**Delete a sample model and minio**
~~~
./script/test/delete-model.sh
~~~

**Uninstall kserve(including ./script/test/delete-model.sh)**
~~~
./script/uninstall/kserve-uninstall.sh
~~~

**Uninstall dependencies**
~~~
./script/uninstall/dependencies-uninstall.sh
~~~
