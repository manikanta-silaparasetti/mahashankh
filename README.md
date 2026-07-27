# MahaSankh AI Design Studio
### API Integration Module — AI Image Generation

> Generate professional design images (Sari, Textile, Carpenter, Flex) from text prompts using AI.

**Live Demo:** [mahasankh.vercel.app](https://mahasankh.vercel.app) *(update after deploy)*  
**API Backend:** [mahasankh-api.onrender.com](https://mahasankh-api.onrender.com) *(update after deploy)*  
**API Docs:** [mahasankh-api.onrender.com/docs](https://mahasankh-api.onrender.com/docs)

---

## Stack

- **Backend:** Python + FastAPI + Uvicorn
- **AI Model:** FLUX (via Pollinations.ai — free, no API key)
- **Image Processing:** Pillow (PNG, TIFF, CMYK, DPI)
- **Frontend:** HTML + Vanilla JS

---

## Run Locally

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Open: `http://localhost:8000`

---

## Deploy

### Backend → Render.com (Free)
1. Go to [render.com](https://render.com) → New → Web Service
2. Connect your GitHub repo
3. Settings:
   - **Build Command:** `pip install -r backend/requirements.txt`
   - **Start Command:** `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Plan:** Free
4. Deploy → copy the URL (e.g. `https://mahasankh-api.onrender.com`)
5. Update `frontend/index.html` line with that URL

### Frontend → Vercel (Free)
1. Go to [vercel.com](https://vercel.com) → Import GitHub repo
2. No build settings needed — `vercel.json` handles it
3. Deploy → get your URL

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Frontend UI |
| GET | `/health` | Health check |
| GET | `/models` | List AI models |
| POST | `/generate` | **Generate design image** |
| POST | `/convert-tiff` | Convert image to TIFF |
| GET | `/docs` | Swagger API docs |

### POST /generate

```json
{
  "prompt": "Red Kanjivaram sari with golden zari border, peacock motifs on pallu",
  "module": "sari",
  "width": 768,
  "height": 768,
  "dpi": 300,
  "convert_tiff": true,
  "color_mode": "RGB"
}
```

Modules: `sari` | `textile` | `carpenter` | `flex` | `general`

---

## Project Structure

```
mahasankh/
├── backend/
│   ├── main.py          ← FastAPI app + AI integration
│   └── requirements.txt
├── frontend/
│   └── index.html       ← UI prototype
├── vercel.json          ← Vercel config
├── render.yaml          ← Render config
└── README.md
```
