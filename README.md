# MovieBox Web App
“MovieBox Web App provides a client-facing API that aggregates metadata, controls playback, and optionally proxies remote media streams without hosting, storing, or distributing any content.”

A modern, cinematic web interface for searching, streaming, and downloading movies, TV series, and anime. Built with FastAPI and React.

To learn more, view the OpenAPI documentation at http://localhost:8000/docs
 after running the backend locally

This page is the OpenAPI (Swagger) documentation for the MovieBox Web App backend.
It lists all available API endpoints used by the frontend to search content, fetch details, stream or download media, and proxy streams, along with their parameters and responses.
The API acts as a controller and proxy layer, connecting the app to an external content API without hosting or storing any media itself.


## Features

- **Cinematic UI**: A premium "Cinematic Dark" theme with glassmorphism effects and smooth animations.
- **Unified Search**: Search across movies, TV series, and anime with a single powerful search bar.
- **Streaming**: Instantly stream content using  player integration.
- **Downloading**: Download content directly to your local machine with progress tracking.
- **Responsive Design**: Optimized for both desktop (laptops) and mobile devices.


🧰 Tech Stack
Backend

FastAPI – High-performance Python web framework for building APIs

Uvicorn – ASGI server for running the FastAPI application

Requests – HTTP client for communicating with external APIs

moviebox-api – External content aggregation API (metadata & stream links)

Python 3.8+

Frontend

React – Component-based UI library

Vite – Fast development build tool

JavaScript (ES6+)

HTML5 / CSS3

Cinematic Dark UI with glassmorphism effects

Media & Streaming

MPV Player – External media player for streaming playback

HTTP Proxy Streaming – Backend proxy endpoint to bypass CORS / 403 issues

Range Request Support – Enables seeking in video streams

API & Architecture

OpenAPI / Swagger – Auto-generated API documentation

RESTful API Design

Controller & Proxy Layer (no media hosting or storage)

Development & Tooling

Node.js 16+

npm

Git


## Prerequisites

Before you begin, ensure you have the following installed:

1.  **Python 3.8+**: For the backend server.
2.  **Node.js 16+**: For the frontend development server.

### 1. Backend Setup

Navigate to the project root directory:

```bash
cd moviebox_web_app
```

Install the required Python dependencies:

```bash
pip install fastapi uvicorn requests moviebox-api
```
*(Note: Ensure `moviebox-api` is properly installed or available in your python path)*

### 2. Frontend Setup

Navigate to the frontend directory:

```bash
cd frontend
```

Install the Node.js dependencies:

```bash
npm install
```

## Running the Application

You need to run both the backend and frontend servers.

### 1. Start the Backend

From the project root (`moviebox_web_app`), run:

```bash
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

The backend API will be available at `http://localhost:8000`.

### 2. Start the Frontend

From the `frontend` directory, run:

```bash
npm run dev -- --host
```

The web application will be available at `http://localhost:5173`.

## Usage

1.  Open `http://localhost:5173` in your browser.
2.  **Search**: Enter a title (e.g., "Naruto", "Inception") in the search bar.
3.  **View Details**: Click on a movie or show card to view details.
4.  **Stream**: Click the "Stream" button to open the video in `mpv` player.
5.  **Download**: Click "Download" to save the file. Progress will be shown in the modal.

## Troubleshooting

-   **Search is slow on first run**: The backend performs a "warmup" routine on startup. Give it a few seconds after starting the server before searching.
-   **Stream fails**: Ensure `mpv` is installed and added to your system's PATH. You can verify this by running `mpv --version` in your terminal.
-   **No results**: Try a different search term. The application relies on the `moviebox-api` for content.

## Project Structure

-   `backend/`: FastAPI backend code.
    -   `api.py`: Core API logic and endpoints.
    -   `main.py`: App entry point and CORS config.
-   `frontend/`: React frontend code.
    -   `src/components/`: Reusable UI components (MovieCard, SearchBar, DetailsModal).
    -   `src/styles/`: Global CSS and design system.

⚠️ Disclaimer

This application does not host or own any media content.

It is a technical demonstration project.

The author does not encourage copyright infringement.

Users are responsible for complying with applicable laws.

🔐 License

This project is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0).
See the LICENSE file for details.
