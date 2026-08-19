# MahaShankh Studio Pro — Complete Technical Documentation

## 1. Project Overview
MahaShankh Studio Pro is a Next-Gen AI Print & Design Engine built to streamline the workflow between digital design and physical print production. Traditional raster images (JPEG, PNG, WebP) often lack the precise DPI, color profiles (CMYK), and high resolution required for industrial printing, textile manufacturing, and CNC machinery. 

This engine solves these issues by providing a deterministic, web-based conversion pipeline that integrates AI-powered background removal and Super-Resolution upscaling (up to 8x), delivering production-ready formats like TIFF and BMP natively to the browser.

---

## 2. Technical Stack

### Frontend Architecture
- **HTML5/CSS3/JS (Vanilla)**: Built without bulky frontend frameworks (like React or Vue) to ensure lightning-fast initial load times.
- **Glassmorphism UI**: A premium, dark-mode aesthetic utilizing modern CSS backdrop-filters, custom glowing micro-animations, and responsive layouts tailored for mobile, tablet, and desktop.
- **Client-Side Blob Generation**: Handles massive file downloads (up to 100MB+) directly in the browser's memory using `URL.createObjectURL(Blob)`, bypassing traditional HTTP download limitations for heavy TIFF files.

### Backend Engine
- **FastAPI**: A modern, high-performance web framework for building APIs with Python based on standard Python type hints. Selected for its asynchronous capabilities and automatic Swagger/OpenAPI documentation.
- **Uvicorn**: An ASGI web server implementation for Python.

### AI & Image Processing Core
- **Pillow (PIL)**: The core engine for format conversion, color space transformations (RGB to CMYK), DPI injection, and Lanczos/Bicubic resizing.
- **Rembg (u2netp model)**: An AI-powered tool to remove image backgrounds seamlessly. We specifically use the ultra-lightweight `u2netp` model (~4.7MB) to ensure fast cold-starts on constrained cloud servers, avoiding the heavy 1GB standard model.
- **ONNX Runtime**: The underlying machine learning inference engine that powers the background removal efficiently on CPUs.
- **SciPy / NumPy / Scikit-Image**: Core mathematical and matrix transformation libraries used by the AI models to process pixel arrays.

---

## 3. System Workflow (Step-by-Step)

When a user uploads an image via the MahaShankh Studio UI, the following pipeline executes:

1. **Client-Side Validation**: The frontend reads the image metadata (size, format) and converts it into a Base64 string or multipart form payload.
2. **API Ingestion (`convert.py`)**: FastAPI receives the payload, and validates it against Pydantic schemas (`ConversionOptions`).
3. **Decompression Bomb Protection**: The `ImageValidator` service checks the image dimensions to prevent malicious files from overwhelming the server memory (preventing DoS attacks).
4. **AI Background Removal (Optional)**: If requested, the image is passed to the `rembg` session. The `u2netp` model identifies the foreground subject and strips the background, converting the image to an RGBA format (transparent).
5. **Super-Resolution Upscaling**: The `PillowUpscaler` service applies the requested upscale factor (1x, 2x, 4x, or 8x). This physically multiplies the pixel density, ensuring the image remains crisp for large-format printing.
6. **Color Space & DPI Injection**: 
   - The `ColorManager` applies the requested color profile (e.g., converting RGB to print-ready CMYK).
   - The `DPIManager` embeds the physical DPI metadata (e.g., 300 DPI or 600 DPI) into the image headers.
7. **Format Export**: The processed matrix is routed to specific exporter classes (`TIFFExporter`, `BMPExporter`, etc.) which handle format-specific compression algorithms (like LZW for TIFF).
8. **Base64 Packaging**: The final binary is encoded back into Base64 and sent to the frontend.
9. **Browser Download Generation**: The frontend converts the Base64 string back into a raw Binary Large Object (Blob) and dynamically creates a hidden `<a>` tag to trigger an instant download of the production file.

---

## 4. Deployment Architecture

The application is currently deployed on **Render** (Free Tier). 

- **Environment**: Python 3.11+
- **Entry Point**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- **Dynamic Package Resolution**: To prevent Python relative-import errors during cloud deployment, `backend/main.py` contains a custom sys-path injection script that dynamically sets the execution context.
- **Memory Management**: Render's free tier provides 512MB of RAM. The architecture is explicitly tuned to stay under this limit by avoiding heavy AI models and cleaning up variables immediately after the HTTP response.

---

## 5. Future Upgrades & Project Roadmap

To scale MahaShankh Studio Pro into a complete enterprise design intelligence cloud, the following upgrades are recommended for Phase 2:

### A. Advanced AI Integration
- **Real-ESRGAN Integration**: Replace standard Pillow resizing with Real-ESRGAN (Enhanced Super-Resolution Generative Adversarial Networks) for true AI upscaling that restores lost textures and details, rather than just duplicating pixels.
- **Stable Diffusion (Inpainting)**: Allow users to automatically fill in missing borders or generate complementary background elements.

### B. CorelDRAW / CNC Features
- **Auto-Vectorization Engine**: Implement a module (using tools like `potrace` or `vtracer`) to convert raster images into clean SVG or DXF files. This is a highly requested "CorelDRAW Killer" feature for CNC routers, laser cutters, and carpentry.
- **Seamless Pattern Generation**: A mathematical module that analyzes an input image and mirrors/tiles it to create infinite, seamless patterns for textile and saree printing.

### C. Infrastructure Scaling
- **Asynchronous Task Queues (Celery + Redis)**: Currently, HTTP requests block until the image is fully processed. For massive 8x upscaling of high-res images, the request might time out. Implementing a Celery queue will allow the backend to process images in the background and notify the frontend via WebSockets when the file is ready.
- **Cloud Storage (AWS S3)**: Stop passing massive Base64 strings over HTTP. Instead, have the backend upload the processed TIFF to an S3 bucket and return a temporary, signed download URL to the user.
- **GPU Acceleration**: Upgrade the deployment environment from Render (CPU-only) to a GPU-backed instance (like AWS EC2 g4dn or RunPod) to accelerate `onnxruntime` and future `Real-ESRGAN` inferences by up to 50x.
