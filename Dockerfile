FROM node:22-bookworm-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    FRONTEND_DIST=/app/frontend/dist WEKA_JAR=/opt/weka/weka-3.8.6.jar \
    STORAGE_DIR=/app/.runtime/storage \
    JAVA_TOOL_OPTIONS="-Xmx128m -XX:MaxMetaspaceSize=96m"
RUN apt-get update && apt-get install -y --no-install-recommends openjdk-17-jdk-headless curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN mkdir -p /opt/weka \
    && curl --fail --location --retry 3 https://repo.maven.apache.org/maven2/nz/ac/waikato/cms/weka/weka-stable/3.8.6/weka-stable-3.8.6.jar -o /opt/weka/weka-3.8.6.jar \
    && echo "932ea2f342b58fe45736389e9c426d5b5955e610d1f5f6485117f532068915e9  /opt/weka/weka-3.8.6.jar" | sha256sum --check
WORKDIR /app
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/ ./backend/
COPY scripts/WekaCheck.java ./scripts/WekaCheck.java
COPY deploy/start.py ./deploy/start.py
COPY --from=frontend /frontend/dist ./frontend/dist/
RUN useradd --create-home --uid 10001 converter && mkdir -p /app/.runtime/storage \
    && chown -R converter:converter /app/.runtime
USER converter
EXPOSE 8000
CMD ["python", "-m", "deploy.start"]
