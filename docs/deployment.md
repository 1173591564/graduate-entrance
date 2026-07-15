# Deployment baseline

The production target is Alibaba Cloud ECS with Docker Compose and Caddy HTTPS.

Before deployment:

1. Replace all local passwords and tokens with protected deployment secrets.
2. Use a dedicated deployer account and SSH key; disable root password login.
3. Bind PostgreSQL, workers and future code-runner services to private networks only.
4. Back up PostgreSQL before migrations and verify restore procedures.
5. Pin image versions, run health checks and retain the previous release for rollback.
6. Configure a real domain and Caddy TLS policy in a production-specific Compose override.

The repository intentionally contains no production credentials or server-specific configuration.
