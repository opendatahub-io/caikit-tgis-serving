# Contributing to Caikit TGIS Serving

Thanks for your interest in this project. You can contribute to this project in many different ways.

## Setting up a MacOS (Apple silicon) development environment

Unfortunately at this point in time development for this project cannot be performed in a MacOS native environment. Support for MacOS is experimental and it should not be considered for production development.

With the scripts and makefile provided in the project only these tasks are known to successfully work:

1. Build the image
2. Update the `poetry.lock` file
3. Execute the smoke test in a virtual environment

The following table provides the matrix of the tools and their versions that are known to work.

|Tool Name|Supported Version|Installation Instructions|
|---|---|---|
| Docker and docker compose | 24.0.6-rd+ | |
| virtualenv| 20.24.6_1 | install via homebrew: `brew install virtualenv`|
| Make | 4.4.1+| install via homebrew: `brew install make` |
| bash | 5.2.21+| install via homebrew: `brew install bash`|

The commands to execute the steps listed above are:

```bash
#To build the image using the docker engine
make default -e ENGINE=docker

#To build the image using podman
make default

#To update the poetry lock file using the docker engine
make refresh-poetry-lock-files -e ENGINE=docker

#To update the poetry lock file using the docker engine
make refresh-poetry-lock-files

#To run the smoke test (from the root of the repo) you will need have a Python 3.9
#virtual environment setup

#Create virtual environment and activate it
virtualenv -p 3.9 venv
source venv/bin/activate

#Run the smoke tests (which use docker compose to start up the servers)
./test/smoke-test.sh
```

Please note that running the smoke tests requires docker compose. Using podman to run the docker compose has not been tested.
