FROM apache/airflow:latest-python3.11

COPY requirements_clean.txt /
RUN pip install --no-cache-dir "apache-airflow==${AIRFLOW_VERSION}" -r /requirements_clean.txt

USER root
RUN mkdir src/

COPY setup.py /src/setup.py
COPY dst_airlines/ /src/dst_airlines/

RUN mkdir -p app/raw_files/
COPY data/4_external/airport_names.csv /app/raw_files/airport_names.csv

RUN pip3 install --no-cache-dir /src
USER airflow