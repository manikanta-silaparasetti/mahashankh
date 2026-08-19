<div align="center">
  <h1>🐚 MahaShankh Studio Pro</h1>
  <p><strong>Next-Gen AI Print & Design Format Conversion Engine</strong></p>

  <p>
    <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi" alt="FastAPI"></a>
    <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"></a>
    <a href="https://render.com/"><img src="https://img.shields.io/badge/Render-%46E3B7?style=for-the-badge&logo=render&logoColor=white" alt="Render"></a>
    <a href="#"><img src="https://img.shields.io/badge/AI_Powered-Background_Removal-8A2BE2?style=for-the-badge" alt="AI Powered"></a>
  </p>
</div>

---

## 📖 Overview

MahaShankh Studio Pro is an industrial-grade, deterministic image transformation engine designed specifically for the print production, textile manufacturing, and CNC machinery industries. 

Traditional digital image formats (JPEG, PNG, WebP) are often incompatible with heavy industrial printers which demand exact DPI metadata, physical dimension scaling, lossless compression, and strict CMYK color profiles. MahaShankh bridges this gap by offering a lightning-fast, web-based UI that processes and exports highly technical formats (like LZW-compressed TIFFs and BMPs) natively to the user's browser.

### ✨ Key Features
- **AI Background Removal**: Seamlessly isolate subjects using the ultra-efficient `u2netp` inference model.
- **8x Super-Resolution Upscaling**: Multiply pixel density physically for massive, crisp large-format printing.
- **Print-Ready CMYK Conversion**: Flawless color space transitions to ensure digital designs match physical ink outputs.
- **Deterministic DPI Injection**: Embed physical metadata (72, 150, 300, 600+ DPI) directly into file headers.
- **Zero-Footprint Frontend**: A stunning, responsive Glassmorphism UI built in Vanilla JS/HTML/CSS. No heavy frontend frameworks required.
- **Client-Side Blob Streaming**: Generates massive downloads (100MB+) locally in browser memory without network timeouts.

---

## 🛠️ Architecture & Tech Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Backend Framework** | `FastAPI` + `Uvicorn` | High-performance asynchronous API engine. |
| **Frontend** | Vanilla `HTML5/CSS3/JS` | Rendered via FastAPI StaticFiles. |
| **Image Engine** | `Pillow (PIL)` | Core matrix manipulation, Lanczos/Bicubic resizing, and DPI setting. |
| **AI Inference** | `rembg` + `onnxruntime` | Executes the `u2netp` machine learning model for background extraction. |
| **Math & Matrices** | `NumPy`, `SciPy` | Underlying array transformations for high-speed pixel manipulation. |

---

## 🚀 Installation & Local Setup

### Prerequisites
- Python 3.10+
- Git

### Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/manikanta-silaparasetti/mahasankh.git
   cd mahasankh
   ```

2. **Create a virtual environment (Recommended):**
   ```bash
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r backend/requirements.txt
   ```

4. **Run the server:**
   ```bash
   uvicorn backend.main:app --host 0.0.0.0 --port 8000
   ```

5. **Access the application:**
   - **Studio UI**: `http://localhost:8000/`
   - **Interactive API Docs**: `http://localhost:8000/docs`

---

## 🚢 Deployment

This application is configured for seamless deployment on **Render** (Web Services).

1. Connect your GitHub repository to Render.
2. Set the **Build Command**:
   ```bash
   pip install -r backend/requirements.txt
   ```
3. Set the **Start Command**:
   ```bash
   uvicorn backend.main:app --host 0.0.0.0 --port $PORT
   ```

> **Note**: The codebase contains a dynamic package resolution script in `backend/main.py` that prevents relative-import errors, meaning `cd backend && uvicorn main:app` will also execute flawlessly on strict cloud environments.

---

## 🔮 Roadmap (Phase 2)

- [ ] **Auto-Vectorization Pipeline**: Convert raster inputs into clean `SVG` or `DXF` paths for CNC machines and laser cutters.
- [ ] **Seamless Pattern Generation**: Mathematical edge-wrapping for continuous textile and saree printing.
- [ ] **Real-ESRGAN Integration**: Replace standard Pillow upscaling with Generative Adversarial Networks for true detail restoration.
- [ ] **Asynchronous Workers**: Implement `Celery` + `Redis` to process massive gigapixel files in the background without HTTP timeouts.

---

<div align="center">
  <p>Built with ❤️ by <strong>Manikanta Silaparasetti</strong> & The MahaShankh Team</p>
</div>
