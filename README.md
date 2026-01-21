# MovieBox Web App

**MovieBox Web App** is a self-hosted web interface for aggregating metadata and controlling media playback. It connects to external APIs to resolve stream URLs and provides a unified frontend for search and discovery.

---

## 🎯 Project Scope

### What this is
-   A **metadata aggregator** that pulls info from MovieBox, HiAnime, and YTS.
-   A **playback controller** that delegates streaming to embedded players or local proxies.
-   A **technical demonstration** of FastAPI and React integration.

### What this is not
-   A content hosting platform.
-   A video distribution service.
-   A commercial product.

---

## ✨ Key Features

### Navigation & UI
-   **Unified Sidebar**: Vertical navigation for switching between standard, anime, and torrent sources.
-   **Source Filtering**: Dedicated views for **MovieBox** (Web), **HiAnime** (Anime), and **CineCLI** (Torrents).
-   **Responsive Layout**: Adapts to different screen sizes with a clean, dark-mode/glassmorphism design.

### Backend Capabilities
-   **CineCLI Integration**: Searches decentralized networks (YTS) with automatic mirror fallback and magnet link resolution.
-   **Proxy Streaming**: `/api/proxy/stream` endpoint supports range requests to bypass CORS restrictions on specific video hosts.
-   **Download Proxy**: `/api/proxy/download` endpoint for facilitating direct file downloads.
-   **System Monitoring**: `/api/system/status` provides real-time health checks of external dependencies.

---

## 🧰 Tech Stack

**Backend**
-   **FastAPI**: Async Python web framework.
-   **HTTPX**: Asynchronous HTTP client.
-   **Uvicorn**: ASGI server implementation.

**Frontend**
-   **React 18**: Frontend library.
-   **Vite**: Build tool and dev server.
-   **CSS Modules**: Component-scoped styling.

---

## 🛠️ Setup & Usage

### Prerequisites
-   Python 3.8+
-   Node.js 16+

### 1. Backend
```bash
cd backend
pip install -r requirements.txt # or install manually: fastapi uvicorn httpx moviebox-api
python -m uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```
*Documentation available at: [http://localhost:8080/docs](http://localhost:8080/docs)*

### 2. Frontend
```bash
cd frontend
npm install
npm run dev -- --host
```
*Access application at: `http://localhost:5173`*

---

## ⚖️ Legal Disclaimer

This software is for educational and research purposes only. The developers of this project do not host, own, or upload any media content. The application acts solely as a client-side interface for existing third-party APIs. Users are responsible for ensuring their usage complies with all applicable local laws and regulations.

## 📄 License

Licensed under the **AGPL-3.0**. See `LICENSE` for details.
