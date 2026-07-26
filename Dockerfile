FROM python:3.14-alpine@sha256:26730869004e2b9c4b9ad09cab8625e81d256d1ce97e72df5520e806b1709f92

# Install system dependencies for Chrome, WebDriver and build tools
RUN apk add --no-cache \
    py3-pip \
    chromium \
    chromium-chromedriver \
    xvfb \
    build-base \
    python3-dev \
    musl-dev \
    pkgconfig \
    openssl-dev \
    libffi-dev \
    rust \
    cargo \
    && rm -rf /var/cache/apk/*

# Set Chrome binary path for Selenium
ENV CHROME_BIN=/usr/bin/chromium-browser
ENV CHROME_PATH=/usr/bin/chromium-browser
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver
ENV DISPLAY=:99

RUN python -m pip install --upgrade pip setuptools wheel maturin

ADD src /app/src

WORKDIR /app/
COPY ["medicony.py", "LICENSE", "pyproject.toml", "/app/"]

ARG VERSION
ENV SETUPTOOLS_SCM_PRETEND_VERSION_FOR_MEDICONY=$VERSION

RUN pip install --no-cache-dir .

ENTRYPOINT ["python", "./medicony.py"]
