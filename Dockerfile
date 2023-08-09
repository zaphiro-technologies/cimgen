FROM alpine
RUN apk update
RUN apk add python3 git py3-pip py3-lxml file
RUN pip3 install --upgrade pip
RUN pip3 install xmltodict chevron

COPY cpp/               /CIMgen/cpp/
COPY java/              /CIMgen/java/
COPY javascript/        /CIMgen/javascript/
COPY python/            /CIMgen/python/
COPY pydantic/            /CIMgen/pydantic/
COPY sqlalchemy/            /CIMgen/sqlalchemy/
COPY CIMgen.py build.py /CIMgen/
COPY cgmes_schema/ /cgmes_schema
WORKDIR /CIMgen
ENTRYPOINT [ "/usr/bin/python3", "build.py", "--outdir=/cgmes_output", "--schemadir=/cgmes_schema" ]
CMD [ "--langdir=cpp" ]
