FROM python:3.12-slim
WORKDIR /app
RUN groupadd --system infraguard && useradd --system --gid infraguard --home-dir /app infraguard
COPY lab/ /app/lab/
USER infraguard
EXPOSE 8088
# ClusterIP-only; no public Ingress or external port. Test-only unauthenticated control endpoint.
CMD ["python", "-m", "lab.server", "--port", "8088", "--host", "0.0.0.0"]
