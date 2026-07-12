# Reference base image for real-environment validation (PRD §11.7, §20).
# The validator control plane launches ephemeral containers FROM images like
# this with: --network none --read-only --pids-limit 256 --memory/--cpus
# quotas --security-opt no-new-privileges, mounting only the scenario fixture.
# Keep this image minimal and dependency-free: scenario fixtures must be
# testable offline (network is disabled at run time).
FROM python:3.11-slim

RUN useradd --create-home --uid 10001 runner
USER runner
WORKDIR /workspace

# No entrypoint: the validator passes scenario-declared argv arrays only.
