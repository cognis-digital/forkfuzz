FROM python:3.12-slim
LABEL org.opencontainers.image.title="cognis-forkfuzz"
LABEL org.opencontainers.image.source="https://github.com/cognis-digital/forkfuzz"
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir .
ENTRYPOINT ["forkfuzz"]
