FROM python:3.10.14

WORKDIR /app

RUN echo hello
CMD ["/bin/bash", "-c", "cd /app && python -m venv .venvd && source .venvd/bin/activate &&  pip install poetry==1.8.2 && poetry install && make run_scheduled"]