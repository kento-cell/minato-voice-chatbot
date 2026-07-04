# Headless "ミナトAPI" image: text-in -> generated speech (WAV) out.
# CPU inference by default, so it runs identically on any machine/architecture
# (no NVIDIA driver / CUDA toolkit required inside the container).
FROM python:3.12-slim

WORKDIR /app

# libsndfile is required by the `soundfile` package (used for WAV I/O in api.py's
# dependency chain / local tooling); harmless if unused at runtime.
RUN apt-get update && apt-get install -y --no-install-recommends libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY characters/ ./characters/

ENV VOICEVOX_URL=http://voicevox:50021
# Inside a container, binding beyond loopback is required for port mapping.
# (Native runs default to 127.0.0.1 -- see src/api.py.)
ENV API_HOST=0.0.0.0
EXPOSE 8080

CMD ["python", "src/api.py"]
