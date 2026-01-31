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

## 🧠 Architecture & Workflows

### 1. MovieBox (Streaming)
*High-quality metadata and direct HTTP streaming.*
-   **How it works**: Combines metadata from TMDB with direct stream links from indexed file hosts.
-   **Stream Button**: Resolves the direct MP4/MKV link and plays it in the integrated player.
-   **Download Button**: Routes the request through the **Backend Download Proxy** (`/api/proxy/download`). This creates a tunnel, allowing you to download files even if the host blocks direct browser downloads (CORS/Referer protection).
-   **Local vs Cloud**:
    -   **Local Mode**: Frontend talks to your running `localhost:8080` server. Recommended for maximum speed and proxy capabilities.
    -   **Cloud Mode**: Frontend connects to a public community instance. Useful if you can't run Python locally.

### 2. CineCLI (Torrents)
*Decentralized P2P network search.*
-   **How it works**: The backend acts as a "Meta-Search Engine" for YTS. It automatically cycles through **10+ active mirrors** (like `yts.lt`, `yts.rs`) to bypass ISP blocks.
-   **Buttons**:
    -   **Magnet**: CineCLI content is P2P-based. Clicking "Magnet" will open your system's default Torrent Client (e.g., qBittorrent, Transmission) to handle the file. It does not stream directly in the browser.

### 3. HiAnime (Anime)
*Specialized Anime scraper.*
-   **How it works**: Scrapes episode lists and IDs from HiAnime.
-   **Stream Button**: Instead of a direct file, it loads a third-party **Embed Player** (iframe) inside the app. This ensures 99% availability for anime episodes without complex proxying.

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


## 🔁 Client-side Routing (Deep Links)

The frontend is a single-page React application that uses React Router for navigation. By default the app is shipped with a hash-based router (`HashRouter`) so deep links work when hosting the built files on simple static servers or via preview services.

Key routes
- `/` — Home / Discover view
- `/details/:id?source=<source>` — Item details modal (source defaults to `moviebox`). Example: `/#/details/dispatches-from-elsewhere-hindi-smkbnADWAJ2?source=moviebox`
- `/watch/:id?season=<n>&episode=<m>` — Watch page for a given item. Example: `/#/watch/3a594f5d-f540-4236-bfd9-73f7b7c1bfa6?episode=1`

Notes
- The watch page syncs the currently selected `season` and `episode` into the URL query string so you can copy/paste or bookmark an exact player state.
- `HashRouter` is used intentionally for compatibility with static hosting. If you prefer clean URLs (no `#`), switch to `BrowserRouter` and configure your server to return `index.html` for unknown paths (SPA fallback).

Testing deep links locally
1. Run the frontend dev server:
```bash
cd frontend
npm run dev
```
2. Open a deep-link in the browser (Vite dev server also serves hash routes):
```text
http://localhost:5173/#/watch/<ITEM_ID>?episode=1
```

Programmatic navigation
- The app uses `useNavigate()` from `react-router-dom` for internal navigation and replaces history entries when updating episode/season so the back button remains intuitive.


This software is for educational and research purposes only. The developers of this project do not host, own, or upload any media content. The application acts solely as a client-side interface for existing third-party APIs. Users are responsible for ensuring their usage complies with all applicable local laws and regulations.

## 📄 License

Licensed under the **AGPL-3.0**. See `LICENSE` for details.
