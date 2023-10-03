FROM caikit-standalone:latest

WORKDIR /tmp

USER root
RUN curl -sL https://github.com/fullstorydev/grpcurl/releases/download/v1.8.7/grpcurl_1.8.7_linux_x86_64.tar.gz | tar zxvf - grpcurl &&  mv grpcurl /usr/bin/

USER caikit

RUN git clone https://huggingface.co/google/flan-t5-small && python -c 'import caikit_nlp; \
model = caikit_nlp.text_generation.TextGeneration.bootstrap("flan-t5-small"); \
model.save("flan-t5-small-caikit")'

RUN mv flan-t5-small-caikit /opt/models/
COPY smoke-test.sh /tmp

CMD ["bash", "/tmp/smoke-test.sh"]
