# Script-based Installation

## Clone the repo


~~~
git clone https://github.com/opendatahub-io/caikit-tgis-serving
cd caikit-tgis-serving/demo/kserve
~~~

**NOTE:** If you would like to use brew, please create a credential secret and ICSP.

## Set the environment variables

If the variables below are not set, the script will ask for them.


- Brew is a registry where WIP images are published. Please look for the desired/correct brew tag, as it changes with every build. 
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

***Description of Variables:***
- **CHECK_UWM:** If you would like to skip the message that checks the User Workload Configmap, set this to `false` .
- **TARGET_OPERATOR:** Can be set to `odh`, `rhods` or `brew`. If not set, the script will ask for it.
- **BREW_TAG:** If using `brew`, set this to desired brew tag (ie. 554169)
- **CUSTOM_MANIFESTS_URL:** If you would like to use a custom manifest, use the URL (ie. https://github.com/opendatahub-io/odh-manifests/tarball/master).
  

# Install Kserve including dependencies

~~~
./scripts/install/kserve-install.sh
~~~

**Uninstall kserve(including ./script/test/delete-model.sh)**
~~~
./script/uninstall/kserve-uninstall.sh
~~~

**Uninstall dependencies**
~~~
./script/uninstall/dependencies-uninstall.sh
~~~
