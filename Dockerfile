FROM python:3.12-slim
WORKDIR /app
COPY send.py railway_entry.py ./
# seed campaigns into the image (runtime copies them to the volume on first boot)
COPY campaigns/ ./campaigns/
ENV STATE_DIR=/data
ENV PYTHONUNBUFFERED=1
# first boot: seed volume from image, then loop forever
CMD ["sh", "-c", "mkdir -p /data/campaigns && cp -n /app/campaigns/*.json /data/campaigns/ 2>/dev/null; python3 railway_entry.py"]
