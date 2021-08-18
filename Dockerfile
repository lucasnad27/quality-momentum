FROM python:3.9.6-slim as base

RUN apt update
RUN apt install git build-essential -y

WORKDIR /quality-momentum

# Dependency setup
RUN pip install --upgrade pip
RUN pip install pip-tools

COPY ./setup/*.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip-sync requirements.txt --pip-args '--no-cache-dir --no-deps'

COPY . /quality-momentum

FROM base as debugger

ENTRYPOINT ["python", "-m", "debugpy", "--listen", "0.0.0.0:5678", "--wait-for-client", "-m"]

FROM base as jupyter
EXPOSE 8888
CMD ["jupyter", "lab", "--NotebookApp.token=''", "--no-browser", "--ip=0.0.0.0", "--allow-root"]

FROM base as primary
ENTRYPOINT ["python", "-m"]
