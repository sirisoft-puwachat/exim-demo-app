FROM python:3.12-slim

WORKDIR /app
COPY app.py .

# path ของไฟล์นับเลข — ใน k8s ให้ mount PVC ที่ /data แล้วใช้ค่านี้ต่อ
ENV COUNT_FILE=/data/count.json \
    PORT=8080 \
    PYTHONUNBUFFERED=1

RUN mkdir -p /data
VOLUME ["/data"]
EXPOSE 8080

CMD ["python", "app.py"]
