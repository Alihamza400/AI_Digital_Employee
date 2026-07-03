FROM python:3.12-slim

# === System deps for Playwright ===
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# === Node.js (for opencode CLI) ===
RUN curl -fsSL https://deb.nodesource.com/setup_24.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# === uv (Python package manager) ===
RUN pip install uv

# === opencode CLI ===
RUN npm install -g opencode-ai

# === Project dependencies ===
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev

# === Playwright (browser + system deps) ===
RUN uv run playwright install-deps chromium && uv run playwright install chromium

# === Application code ===
COPY . .

# === Default vault templates (copied into volume on first run) ===
RUN mkdir -p /app/default-vault && \
    if [ -d /app/AI_Employee_Vault ]; then \
        cp -r /app/AI_Employee_Vault/* /app/default-vault/ 2>/dev/null || true; \
    fi

RUN chmod +x /app/entrypoint.sh

EXPOSE 8080

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uv", "run", "python", "main.py"]
