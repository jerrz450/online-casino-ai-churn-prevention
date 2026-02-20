FROM python:3.12-slim

WORKDIR /app

RUN echo 'Acquire::ForceIPv4 "true";' > /etc/apt/apt.conf.d/99force-ipv4 \
 && apt-get update \
 && apt-get install -y ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --upgrade pip

COPY simulator_server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY simulation/ simulation/
COPY simulator_server/ simulator_server/

CMD ["python", "-m", "simulator_server.main"]
