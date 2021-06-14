FROM python:3.8.10-slim

RUN apt update
RUN apt install build-essential -y

WORKDIR /quality-momentum
ADD . /quality-momentum

EXPOSE 8888
# Dependency setup
# Much can be done reduce the size of this container if needed
RUN pip install --upgrade pip
RUN pip install pip-tools

RUN --mount=type=cache,target=/root/.cache \
    pip-sync setup/requirements.txt setup/local-requirements.txt setup/testing-requirements.txt --pip-args '--no-cache-dir --no-deps'

# Run app.py when the container launches
# CMD ["jupyter", "lab", "--NotebookApp.token=''", "--no-browser", "--ip=0.0.0.0", "--allow-root"]