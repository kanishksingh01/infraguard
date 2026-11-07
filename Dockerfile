FROM python:3.12-slim
WORKDIR /app
RUN groupadd --gid 10001 infraguard && useradd --uid 10001 --gid 10001 --no-create-home infraguard
COPY lab/ /app/lab/
USER 10001:10001
EXPOSE 8088
# ClusterIP-only; no public Ingress or external port. Test-only unauthenticated control endpoint.
CMD ["python", "-m", "lab.server", "--port", "8088", "--host", "0.0.0.0"]
