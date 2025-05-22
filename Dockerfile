FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies and pipx
RUN apt-get update && apt-get install -y \
    curl \
    bash \
    build-essential \
    libssl-dev \
    libffi-dev \
    ssh \
    python3-pip \
    && pip install pipx \
    && pipx ensurepath \
    && rm -rf /var/lib/apt/lists/*

# Ensure pipx-installed tools are on PATH
ENV PATH="/root/.local/bin:$PATH"

# Install uv via pipx
RUN pipx install uv

#Setup SSH (optional)
COPY id_ed25519 /root/.ssh/id_ed25519
#COPY id_rsa /root/.ssh/id_rsa
COPY config /root/.ssh/config
#RUN chmod 600 /root/.ssh/id_rsa && chmod 644 /root/.ssh/config
RUN chmod 600 /root/.ssh/id_ed25519 && chmod 644 /root/.ssh/config
#RUN chmod 644 /root/.ssh/config

# Set working directory
WORKDIR /app

# Copy pyproject.toml and uv.lock only
COPY pyproject.toml uv.lock ./

# Create virtual environment and install dependencies from pyproject
RUN uv venv && uv pip install .

# Copy all application files
COPY . .

# Make shell scripts executable
RUN chmod +x ./start.sh ./stop.sh

# Expose necessary ports
EXPOSE 8768 15672 22

# Default command
#CMD ["/bin/bash"]
CMD ["uv", "run", "server.py"]
