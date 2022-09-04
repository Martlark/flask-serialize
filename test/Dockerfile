FROM python:3.10
# runs from this dir
WORKDIR /app
# upgrade pip
RUN pip install -U pip

# mssql driver install
COPY ./test/install-mssql-17-driver.sh /tmp
RUN bash /tmp/install-mssql-17-driver.sh

# engines
COPY ./test/engine_requirements.txt /tmp
RUN pip install -r /tmp/engine_requirements.txt

# copy over our app code
COPY . /app

RUN mkdir -p /persist
RUN apt-get update

# start server

ENTRYPOINT [ "bash", "resources/entrypoint.sh" ]
