# Dockerfile for Authoricy Engine
# Uses Python with WeasyPrint system dependencies

FROM python:3.12-slim

# Install WeasyPrint system dependencies and fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    libglib2.0-0 \
    shared-mime-info \
    # Base fonts
    fonts-liberation \
    # Noto fonts for comprehensive Unicode support
    fonts-noto-core \
    fonts-noto-ui-core \
    # Symbol and emoji fonts
    fonts-symbola \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/* \
    && fc-cache -f -v

# Set working directory
WORKDIR /app

# Copy requirements first (for caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "api.analyze:app", "--host", "0.0.0.0", "--port", "8000"]
