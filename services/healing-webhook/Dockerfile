# healing-webhook — receives alerts from Alertmanager + probe failures from
# testql-watchdog, decides whether to run redsl gate / redsl improve / rebuild
# restore. Delegates the actual dispatch to the host docker.sock so it can
# spin up short-lived `semcod/redsl:local` / `semcod/rebuild:local` containers
# on demand.

FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl docker.io \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
      fastapi==0.115.0 \
      uvicorn[standard]==0.32.0 \
      prometheus-client==0.20.0 \
      httpx==0.27.2 \
      pydantic==2.9.2 \
      planfile==0.1.117 \
      vallm>=0.1.87 \
      "redup>=0.4.15" \
      PyYAML==6.0.2

COPY app.py ticket_builder.py /app/

ENV REPO_PATH=/repo \
    REDSL_IMAGE=semcod/redsl:local \
    REBUILD_IMAGE=semcod/rebuild:local \
    DRY_RUN=true \
    PORT=8810

EXPOSE 8810

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8810"]
