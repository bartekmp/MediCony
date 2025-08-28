FROM python:3.13-alpine

# Install system dependencies for Chrome and WebDriver
RUN apk add --no-cache \
    py3-pip \
    chromium \
    chromium-chromedriver \
    xvfb \
    && rm -rf /var/cache/apk/*

# Set Chrome binary path for Selenium
ENV CHROME_BIN=/usr/bin/chromium-browser
ENV CHROME_PATH=/usr/bin/chromium-browser
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver
ENV DISPLAY=:99

ADD src /app/src

WORKDIR /app/
COPY ["medicony.py", "LICENSE", "pyproject.toml", "/app/"]

ARG VERSION
ENV SETUPTOOLS_SCM_PRETEND_VERSION_FOR_MEDICONY=$VERSION

RUN pip install --no-cache-dir setuptools && \
    pip install --no-cache-dir .

ENTRYPOINT ["python", "./medicony.py"]
