FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY services/planning_foundation/requirements.txt /tmp/planning-requirements.txt
COPY services/agent_runtime/requirements.txt /tmp/runtime-requirements.txt
RUN pip install --no-cache-dir \
    -r /tmp/planning-requirements.txt \
    -r /tmp/runtime-requirements.txt \
    uvicorn==0.52.4

COPY services /app/services

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "services.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
