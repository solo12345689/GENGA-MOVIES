# MovieBox Web App

**MovieBox Web App** is a modern, cinematic interface that aggregates metadata, controls playback, and proxies remote media streams. It acts as a "Headless Controller" for your media, connecting to external APIs (MovieBox, YTS, HiAnime) without hosting or distributing content itself.

> **Note**: This application is a technical demonstration. It does not host any media files.

---

## 🚀 New Features (v2.0)

### 🧭 Sidebar Navigation
-   **Unified Sidebar**: A new, collapsible vertical navigation bar replaces the old top tabs.
-   **Source Switching**: Easily toggle between **Home**, **MovieBox** (Streaming), **HiAnime** (Anime), and **CineCLI** (Torrents).
-   **Server Status**: Real-time system status indicator for backend health.

### 🧲 CineCLI Integration
-   **Torrent Search**: Seamlessly search YTS/CineCLI for torrents directly from the unified search bar.
-   **Robust Mirror Fallback**: The backend automatically rotates through 10+ YTS mirrors (`yts.mx`, `yts.lt`, `yts.rs`, etc.) to ensure connectivity, even if some domains are blocked.
-   **Magnet Resolution**: Instantly resolves magnet links for external downloaders.

### 🛡️ Enhanced Proxy & Streaming
-   **Smart Proxy**: New `/api/proxy/stream` endpoint supports **Range Requests**, allowing you to seek/scrub through proxy-streamed videos.
-   **Download Proxy**: Dedicated `/api/proxy/download` endpoint to force-download remote content.
-   **Anti-Blocking**: Backend automatically spoofs User-Agents and manages headers to bypass basic hotlink protections.

---

## 🌐 Overview

The architecture is designed to be lightweight and modular:

1.  **Backend (FastAPI)**: Acts as the "Brain". It searches external APIs, resolves stream URLs, and proxies difficult connections.
2.  **Frontend (React)**: Handles the UI, state, and specialized players for different content types.
3.  **Media**: Streamed via **Local Proxy** (MovieBox mode) or **Cloud Embeds** (HiAnime mode).

### Application Modes

| Mode | Description |
| :--- | :--- |
| **🎥 MovieBox** | Uses the **Local Backend** to fetch high-quality HTTP streams. Supports proxying for maximum compatibility. |
| **🍥 HiAnime** | Lightweight mode. Extracts episode IDs and uses 3rd-party embed players (iframe). |
| **🧲 CineCLI** | **NEW!** Searches decentralized torrent networks (YTS) for magnet links. |

---

## 🧰 Tech Stack

### Backend
-   **FastAPI**: High-performance Async IO.
-   **HTTPX**: Modern, async HTTP client (replaces Requests for better concurrency).
-   **Uvicorn**: ASGI Server.
-   **moviebox-api**: Content aggregation.

### Frontend
-   **React 18**: Component-based UI.
-   **Vite**: Next-gen tooling.
-   **Glassmorphism UI**: Custom CSS variables for a premium, dark-mode aesthetic.

---

## 🛠️ Setup & Installation

### Prerequisites
-   **Python 3.8+**
-   **Node.js 16+**

### 1. Backend Setup
```bash
cd moviebox_web_app/backend

# Install dependencies
pip install fastapi uvicorn httpx moviebox-api

# Run the server
python -m uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```
*Port 8080 is the default for the backend API.*

> **Tip**: You can view the full interactive API documentation (Swagger UI) at [http://localhost:8080/docs](http://localhost:8080/docs) when the backend is running.

### 2. Frontend Setup
```bash
cd moviebox_web_app/frontend

# Install dependencies
npm install

# Run the dev server
npm run dev -- --host
```
*Access the web app at `http://localhost:5173`.*

---

## 🎮 Usage Guide

1.  **Search**: Use the top search bar.
    -   *Default*: Searches all unified sources.
    -   *CineCLI*: Switching to the CineCLI tab targets YTS torrents specifically.
2.  **Sidebar Toggle**: Use the arrow icon in the sidebar to collapse it for a "Theater Mode" view.
3.  **Server Toggle**: In the top right, switch between **Cloud** (Remote API) and **Local** (Your machine).
    -   *Visible only in Home/MovieBox sections.*
4.  **Streaming**:
    -   Click "Stream" to open the internal player (or mpv if configured).
    -   For Anime, use the Season/Episode selector.
5.  **Downloads**:
    -   Click the "Download" button to save media via the backend proxy.

---

## ⚖️ Disclaimer & License

**Disclaimer**: This project does not host, store, or distribute any media content. It is a search engine and proxy tool for publicly available APIs. Users are responsible for their own usage and compliance with local laws.

**License**: GNU Affero General Public License v3.0 (AGPL-3.0).
