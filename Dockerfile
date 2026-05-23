FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY tracker.py .

RUN useradd -r tracker && chown tracker /app
USER tracker

CMD ["python", "-u", "tracker.py"]
