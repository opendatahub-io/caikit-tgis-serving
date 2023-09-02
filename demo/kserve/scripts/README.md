# Script-based installation of Kserve and dependencies

Note: You have the alternative option of installing the KServe/Caikit/TGIS stack by using [Step-by-step commands](demo/kserve/install-manual.md).

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
   
   **CUSTOM_MANIFESTS_URL:** (optional) To use a custom manifest, set the value to the custom manifest URL, for example:
     ~~~
     export CUSTOM_MANIFESTS_URL=https://github.com/opendatahub-io/odh-manifests/tarball/master
     ~~~
   

3. Run the script to install Kserve including its dependencies.

   ~~~
   ./scripts/install/kserve-install.sh
   ~~~

# Script-based uninstall of Kserve and dependencies

1. Uninstall kserve (including `./script/test/delete-model.sh`):

   ~~~
   ./script/uninstall/kserve-uninstall.sh
   ~~~

2. Uninstall the dependencies:

   ~~~
   ./script/uninstall/dependencies-uninstall.sh
   ~~~
