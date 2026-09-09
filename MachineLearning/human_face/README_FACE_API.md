# Face API

Run on Raspberry Pi from this directory:

```bash
cd ~/human_face/human_face
source ../.venv/bin/activate
python face_api.py
```

Health check:

```bash
curl http://127.0.0.1:5001/health
```

Verify a face image:

```bash
curl -X POST http://127.0.0.1:5001/api/face/verify \
  -F "image=@./test/test_1.png"
```

Expected response:

```json
{
  "matched": true,
  "identity": "./id/id_1.png",
  "distance": 0.6723,
  "threshold": 0.8
}
```

Optional environment variables:

```bash
export FACE_API_PORT=5001
export FACE_DB_PATH=./id
export FACE_THRESHOLD=0.8
export FACE_MODEL_NAME=ArcFace
export FACE_DETECTOR=retinaface
export FACE_DISTANCE_METRIC=cosine
```
