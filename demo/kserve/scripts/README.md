# Script-based installation of Kserve and dependencies

Note: You have the alternative option of installing the KServe/Caikit/TGIS stack by using [Step-by-step commands](../../kserve/install-manual.md).

**Prerequisites**

- To support inferencing, your cluster needs a node with 4 CPUs and 8 GB memory.
- You have cluster administrator permissions.
- You have installed the OpenShift CLI (`oc`).

**Procedure**

1. Clone the `caikit-tgis-serving` repo.
   ~~~
   git clone https://github.com/opendatahub-io/caikit-tgis-serving
   cd caikit-tgis-serving/demo/kserve
   ~~~

2. Set environment variables.

   Note: If you do not set values for these variables before you run the script, the script asks for them.

   **TARGET_OPERATOR:** Possible values are `odh` or `rhods`. For example:
   - Red Hat OpenSHift Data Science (1.32+)
     ~~~
     export TARGET_OPERATOR=rhods
     ~~~

   - Open Data Hub (1.9+)
     ~~~
     export TARGET_OPERATOR=odh
     ~~~
  
   **CHECK_UWM:** (optional) To skip the message that checks the User Workload Configmap, set the value to `false`.
     ~~~
     export CHECK_UWM=false
     ~~~
   
   **CUSTOM_MANIFESTS_URL:** (optional) To use a custom manifest, set the value to the custom manifest URL
     ~~~
     export CUSTOM_MANIFESTS_URL=https://github.com/opendatahub-io/odh-manifests/tarball/master
     ~~~
   
   **CUSTOM_CERT,CUSTOM_KEY:** (optional) To use a custom cert/key for knative gateway, set the custom cert path and key path
     ~~~
     export CUSTOM_CERT=/path/to/custom.cert
     export CUSTOM_KEY=/path/to/custom.key
     ~~~   

   **DEPLOY_ODH_OPERATOR:** (optional) Not to deploy odh/rhods operator, set this to false. (default is true)
     ~~~
     export DEPLOY_ODH_OPERATOR=false
     ~~~   
   
   **CLEAN_NS** (optional) Set this to true, if you want to remove the namespace that run odh/rhods applications.(default is false)
     ~~~
     export CLEAN_NS=true
     ~~~

3. Run the script to install Kserve including its dependencies.

   ~~~
   ./scripts/install/kserve-install.sh
   ~~~

*Tips.*
The installation script `kserve-install.sh` consists of four files, and each file plays the following role.
- ./scripts/install/check-env-variables.sh
  - This file checks to see if the environment variables required by the installation script are already provided and requests that information inline if that information is not available. 
- ./scripts/install/1-prerequisite-operators.sh
  - This file installs Serverless and ServiceMesh operator, kserve's dependent operators.   
- ./scripts/install/2-required-crs.sh
  - This file installs ServiceMesh, Serverless CRs, and additional manifests for KServe to operate properly.
- ./scripts/install/3-only-kserve-install.sh
  - This file installs OpenDatahub or RHODS operator and installs KServe by creating DataScienceCluster CR.

# Script-based uninstall of Kserve and dependencies

1. Uninstall kserve (including `./script/test/delete-model.sh`):

   ~~~
   ./scripts/uninstall/kserve-uninstall.sh
   ~~~

2. Uninstall the dependencies:

   ~~~
   ./scripts/uninstall/dependencies-uninstall.sh
   ~~~
