# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## ภาพรวม

Webapp นับเลขอย่างง่าย มี 2 ปุ่ม คือ "นับเลข +" และ "รีเซ็ต" สร้างขึ้นเพื่อใช้ทดสอบ **Kubernetes PVC** ในอนาคต
จึงต้องรักษาข้อจำกัดเหล่านี้ไว้:

- **ห้ามใช้ Postgres หรือ DB ใดๆ** — เก็บสถานะในไฟล์ JSON เท่านั้น
- ใช้ Python stdlib ล้วน (ไม่มี `requirements.txt`) — อย่าเพิ่ม dependency โดยไม่จำเป็น

## คำสั่งที่ใช้บ่อย

```bash
# รันในเครื่อง (ค่า default: ./data/count.json, พอร์ต 8080)
python3 app.py
COUNT_FILE=/tmp/count.json PORT=9000 python3 app.py

# Docker
docker build -t simple-counter .
docker run -p 8080:8080 -v counter-data:/data simple-counter
```

ยังไม่มี test/lint — ทดสอบด้วย `curl`:

```bash
curl -XPOST localhost:8080/api/increment
curl -XPOST localhost:8080/api/reset
curl localhost:8080/api/count
```

## สถาปัตยกรรม

ทั้งแอปอยู่ใน `app.py` ไฟล์เดียว (HTML หน้าเว็บฝังเป็นสตริง `PAGE`):

- Endpoint: `GET /` (หน้าเว็บ), `GET /api/count`, `POST /api/increment`, `POST /api/reset`, `GET /healthz` (สำหรับ probe)
- **ทุกการอ่าน/เขียนผ่านฟังก์ชัน `update_state()`** ซึ่งใช้ `flock` ล็อกไฟล์ เพื่อกัน race เมื่อมีหลาย request/หลาย pod ใช้ volume เดียวกัน
- ไฟล์ถูกเขียนทับ **ตรงๆ** (open → truncate → write → fsync) ไม่ใช้ temp file + `rename` โดยตั้งใจ
  เพราะถ้า k8s mount ไฟล์แบบ `subPath` การ rename ทับไฟล์จะล้มเหลว — อย่าเปลี่ยนเป็น atomic rename
- ถ้าไฟล์ไม่มี/ว่าง/เสีย จะ fallback เป็น `current_number: 0` และสร้างไฟล์ (รวมถึงโฟลเดอร์แม่) ให้เอง

### รูปแบบไฟล์ `count.json`

```json
{"current_number": 12, "last_click_time": "2026-01-01 12:00:00"}
```

- `last_click_time` รูปแบบ `%Y-%m-%d %H:%M:%S` ตามเวลา local ของ container (ตั้ง `TZ` ถ้าต้องการ)
- ปุ่มรีเซ็ตตั้ง `current_number` เป็น 0 และอัปเดต `last_click_time` ด้วย

## Environment variables

| ตัวแปร | ค่า default (local) | ค่าใน Dockerfile | หน้าที่ |
|---|---|---|---|
| `COUNT_FILE` | `./data/count.json` | `/data/count.json` | path ของไฟล์สถานะ (mount PVC ที่ `/data`) |
| `PORT` | `8080` | `8080` | พอร์ตที่ฟัง |

## Docker / Kubernetes

- `Dockerfile` ใช้ `python:3.12-slim`, ประกาศ `VOLUME /data` — ตอน deploy ให้ mount PVC ที่ `/data`
  (หรือ override `COUNT_FILE` ให้ชี้ไปที่ path อื่นที่ mount ไว้)
- container รันเป็น root; ถ้าจะเปลี่ยนเป็น non-root ใน k8s ต้องตั้ง `fsGroup` ให้ PVC เขียนได้
