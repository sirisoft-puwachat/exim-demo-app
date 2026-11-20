# Simple Counter

Webapp นับเลขอย่างง่าย (ปุ่ม "นับเลข +" และ "รีเซ็ต") เก็บสถานะในไฟล์ JSON เพื่อใช้ทดสอบ Kubernetes PVC

## รันในเครื่อง

```bash
python3 app.py
# หรือกำหนดค่าเอง
COUNT_FILE=/tmp/count.json PORT=9000 python3 app.py
```

## Build / Tag / Push ไปยัง Docker Hub

Image ปลายทางคือ `puwachatsrs/exim-demo-app` — แทนที่ `v1.0` ด้วยเวอร์ชันที่ต้องการ

### 1. Login

```bash
docker login
```

### 2. Build image

```bash
docker build -t exim-demo-app:v1.0 .
```

### 3. Tag image

```bash
docker tag exim-demo-app:v1.0 puwachatsrs/exim-demo-app:v1.0
docker tag exim-demo-app:v1.0 puwachatsrs/exim-demo-app:latest
```

### 4. Push ไปยัง Docker Hub

```bash
docker push puwachatsrs/exim-demo-app:v1.0
docker push puwachatsrs/exim-demo-app:latest
```

### แบบสั้น (build พร้อม tag แล้ว push)

```bash
docker build -t puwachatsrs/exim-demo-app:v1.0 -t puwachatsrs/exim-demo-app:latest .
docker push --all-tags puwachatsrs/exim-demo-app
```

### Build แบบ multi-platform (เช่น build บน Mac M1 แต่ deploy บน amd64)

```bash
docker buildx build --platform linux/amd64,linux/arm64 \
  -t puwachatsrs/exim-demo-app:v1.0 \
  -t puwachatsrs/exim-demo-app:latest \
  --push .
```

## Push อัตโนมัติด้วย GitHub Actions

workflow `.github/workflows/docker-push.yml` จะ build และ push `puwachatsrs/exim-demo-app` เมื่อ push เข้า `main` หรือสร้าง tag `v*`
ต้องตั้ง repository secrets: `DOCKERHUB_USERNAME` และ `DOCKERHUB_TOKEN`

## ทดสอบ image ที่ push แล้ว

```bash
docker run -p 8080:8080 -v counter-data:/data puwachatsrs/exim-demo-app:v1.0

curl -XPOST localhost:8080/api/increment
curl localhost:8080/api/count
curl -XPOST localhost:8080/api/reset
```

## Environment variables

| ตัวแปร | ค่า default (local) | ค่าใน Dockerfile | หน้าที่ |
|---|---|---|---|
| `COUNT_FILE` | `./data/count.json` | `/data/count.json` | path ของไฟล์สถานะ (mount PVC ที่ `/data`) |
| `PORT` | `8080` | `8080` | พอร์ตที่ฟัง |
# exim-demp-app
