# Copyright The Caikit Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Setup to be able to build caikit_tgis_backend library.
"""
# Standard
import os

# Third Party
import setuptools.command.build_py

# get version of library
LIBRARY_VERSION = os.getenv("LIBRARY_VERSION")
if not LIBRARY_VERSION:
    raise RuntimeError("LIBRARY_VERSION must be set")

# base directory containing caikit (location of this file)
base_dir = os.path.dirname(os.path.realpath(__file__))

# read requirements from file
with open(os.path.join(base_dir, "requirements.txt"), encoding="utf-8") as filehandle:
    requirements = filehandle.read().splitlines()

setuptools.setup(
    name="caikit-tgis-backend",
    author="caikit",
    version=LIBRARY_VERSION,
    python_requires=">=3.8",
    license="Copyright Caikit Authors 2023 -- All rights reserved.",
    description="Caikit module backend for models run in TGIS",
    install_requires=requirements,
    packages=setuptools.find_packages(include=("caikit_tgis_backend*",)),
    data_files=[os.path.join("caikit_tgis_backend", "generation.proto")],
    include_package_data=True,
)
