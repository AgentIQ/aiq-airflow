# VERSION 1.10.4
# AUTHOR: Matthieu "Puckel_" Roisil
# DESCRIPTION: Basic Airflow container
# BUILD: docker build --rm -t puckel/docker-airflow .
# SOURCE: https://github.com/puckel/docker-airflow

#FROM docker:19.03.5-dind
FROM billyteves/ubuntu-dind:16.04


# Never prompts the user for choices on installation/configuration of packages
ENV DEBIAN_FRONTEND noninteractive
ENV TERM linux

# Airflow
ARG AIRFLOW_VERSION=1.10.4
ARG AIRFLOW_USER_HOME=/usr/local/airflow
ARG AIRFLOW_DEPS=""
ARG PYTHON_DEPS=""
ENV AIRFLOW_HOME=${AIRFLOW_USER_HOME}

# Define en_US.
ENV LANGUAGE en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LC_ALL C
ENV LC_CTYPE C
ENV LC_MESSAGES C

RUN add-apt-repository ppa:jonathonf/python-3.6

RUN set -ex \
    && buildDeps=' \
        freetds-dev \
        libkrb5-dev \
        libsasl2-dev \
        libssl-dev \
        libffi-dev \
        libpq-dev \
        git \
    ' \
    && apt-get update -yqq \
    && apt-get upgrade -yqq 

RUN apt-get install -y python3.6 python3-pip  python3.6-dev
RUN ln -s /usr/bin/pip3 /usr/bin/pip
RUN apt-get install -y apt-utils
RUN apt-get install -yqq --no-install-recommends \
        $buildDeps \
        freetds-bin \
        build-essential \
        curl \
        rsync \
        netcat \
        locales \
        jq \
    && if [ -n "${PYTHON_DEPS}" ]; then pip install ${PYTHON_DEPS}; fi

RUN pip install -U pip
RUN pip install -U setuptools wheel \
  && pip install pytz \
  && pip install pyOpenSSL \
  && pip install ndg-httpsclient \
  && pip install flake8 \
  && pip install pytest \
  && pip install pyasn1

RUN apt-get install -y python3-dev

RUN pip install apache-airflow[crypto,celery,postgres,hive,jdbc,ssh${AIRFLOW_DEPS:+,}${AIRFLOW_DEPS}]==${AIRFLOW_VERSION} \
    && pip install 'redis==3.2'


RUN apt-get purge --auto-remove -yqq $buildDeps \
    && apt-get autoremove -yqq --purge \
    && apt-get clean \
    && rm -rf \
        /var/lib/apt/lists/* \
        /tmp/* \
        /var/tmp/* \
        /usr/share/man \
        /usr/share/doc \
        /usr/share/doc-base
 
COPY script/entrypoint.sh /entrypoint.sh
COPY script/startup.sh /startup.sh
COPY airflow_config/airflow.cfg ${AIRFLOW_USER_HOME}/airflow.cfg
COPY ./dags /usr/local/airflow/dags
COPY Makefile /usr/local/airflow/Makefile
COPY ./tests /usr/local/airflow/tests

#RUN chown -R airflow: ${AIRFLOW_USER_HOME}

EXPOSE 8080 5555 8793

#USER airflow

WORKDIR ${AIRFLOW_USER_HOME}
ENTRYPOINT ["/entrypoint.sh"]
CMD ["/startup.sh", "webserver"] # set default arg for entrypoint
