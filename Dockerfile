FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV ROSETTA_RUNTIME_DIR=/opt/rosetta/runtime

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

COPY streamlit_app.py README.md ./
COPY app ./app
COPY assets ./assets
COPY configs ./configs
COPY .streamlit/config.toml ./.streamlit/config.toml

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
