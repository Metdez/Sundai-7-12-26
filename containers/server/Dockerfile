# Agent Debugger core server (PRD §17/§18). The image contains no model
# weights; simulation providers are reached over the network by configuration.
FROM python:3.12-slim

RUN useradd --create-home --uid 10001 appuser
WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY web/dist ./web/dist
COPY scenarios ./scenarios
COPY configs ./configs

RUN pip install --no-cache-dir .

USER appuser
ENV ADBG_WORKSPACE=/home/appuser/workspace
EXPOSE 8321

# Initialize a workspace on first start, then serve API + dashboard.
CMD ["sh", "-c", "if [ ! -f \"$ADBG_WORKSPACE/agent-debugger.yaml\" ]; then agent-debugger init \"$ADBG_WORKSPACE\"; fi && agent-debugger --workspace \"$ADBG_WORKSPACE\" serve --host 0.0.0.0 --port 8321"]
