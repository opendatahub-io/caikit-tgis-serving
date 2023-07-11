FROM quay.io/opendatahub/text-generation-inference

WORKDIR /caikit
COPY caikit /caikit

# caikit-nlp has caikit and caikit-tgis-backend as dependencies
# In future this will be replaced with just standard pip installs 
RUN yum -y install git && \
    pip install pipenv && \
    pipenv install --system && \
    mkdir -p /opt/models && \
    adduser caikit && \
    chown -R caikit:caikit /caikit /opt/models

USER caikit

ENV RUNTIME_LIBRARY='caikit_nlp' \
    RUNTIME_LOCAL_MODELS_DIR='/opt/models'

CMD [ "./start-serving.sh" ]
