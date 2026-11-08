FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir httpx pydantic numpy cryptography
EXPOSE 8080 9090
CMD ["python", "server.py"]
