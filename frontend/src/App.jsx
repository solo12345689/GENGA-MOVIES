import React, { useState, useEffect } from 'react';
import SearchBar from './components/SearchBar';
import MovieCard from './components/MovieCard';
import DetailsModal from './components/DetailsModal';
import WatchPage from './components/WatchPage';
import './styles/index.css';

// Auto-detect local server IP
const detectLocalServer = async (onProgress) => {
    const hostname = window.location.hostname;

    // Check specific IP and port
    const checkIP = async (ip, port = 8000) => {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 500); // 500ms timeout

            const response = await fetch(`http://${ip}:${port}/api/health`, {
                method: 'GET',
                signal: controller.signal
            });
            clearTimeout(timeoutId);
            if (response.ok) {
                return `http://${ip}:${port}`;
            }
        } catch (e) {
            // Ignore errors
        }
        return null;
    };

    // 1. First check the current hostname on common ports (8000, 8080)
    if (onProgress) onProgress(`Checking ${hostname}...`);
    const port8000 = await checkIP(hostname, 8000);
    if (port8000) return port8000;

    const port8080 = await checkIP(hostname, 8080);
    if (port8080) return port8080;

    // 2. Scan local network subnets (only check port 8000/8080 for discovery)
    // We prioritize 8000 for scanning to be fast
    const subnets = [
        '192.168.0',
        '192.168.1',
        '192.168.31',
        '192.168.100',
        '10.0.0'
    ];

    for (const subnet of subnets) {
        if (onProgress) onProgress(`Scanning ${subnet}.x...`);

        // Scan 255 IPs in chunks of 20
        const ips = Array.from({ length: 255 }, (_, i) => `${subnet}.${i + 1}`);
        const chunkSize = 20;

        for (let i = 0; i < ips.length; i += chunkSize) {
            const chunk = ips.slice(i, i + chunkSize);
            // Check port 8000 first, then 8080
            const promises = chunk.flatMap(ip => [checkIP(ip, 8000), checkIP(ip, 8080)]);
            const results = await Promise.all(promises);
            const found = results.find(url => url);
            if (found) {
                console.log(`Found local server at ${found}`);
                return found;
            }
        }
    }

    // Fallback to localhost:8000 if nothing else found
    // Or try localhost:8080 last resort
    const local8080 = await checkIP('localhost', 8080);
    if (local8080) return local8080;

    return 'http://localhost:8000';
};

// Define available backends
const BACKENDS = {
    local: null, // Will be set dynamically
    cloud: 'https://moviebox-3xxv.onrender.com'
};

function App() {
    // State for server selection (persist in localStorage)
    const [serverMode, setServerMode] = useState(() => {
        return localStorage.getItem('moviebox_server_mode') || 'cloud';
    });

    const [localServerURL, setLocalServerURL] = useState(() => {
        return localStorage.getItem('moviebox_local_ip') || 'http://localhost:8000';
    });

    const [scanningStatus, setScanningStatus] = useState('');
    const [showManualIP, setShowManualIP] = useState(false);
    const [showHistoryModal, setShowHistoryModal] = useState(false);
    const [manualIPInput, setManualIPInput] = useState('');

    // Auto-detect local server on mount
    useEffect(() => {
        // Only scan if we don't have a saved IP or if explicitly requested
        const savedIP = localStorage.getItem('moviebox_local_ip');
        // Force rescan if no IP, or if IP is using old stale ports (8000, 8001, 5500)
        const isStale = savedIP && (savedIP.includes(':8001') || savedIP.includes(':5500'));

        if (!savedIP || savedIP === 'http://localhost:8000' || isStale) {
            setScanningStatus('Scanning network...');
            detectLocalServer((status) => setScanningStatus(status)).then(url => {
                setLocalServerURL(url);
                BACKENDS.local = url;
                setScanningStatus('');
                if (url !== 'http://localhost:8000') {
                    localStorage.setItem('moviebox_local_ip', url);
                }
            });
        } else {
            BACKENDS.local = savedIP;
        }
    }, []);

    const API_BASE = serverMode === 'local' ? localServerURL : BACKENDS[serverMode];

    const [results, setResults] = useState([]);
    const [loading, setLoading] = useState(false);
    const [selectedItem, setSelectedItem] = useState(null);
    const [detailsLoading, setDetailsLoading] = useState(false);
    const [downloadProgress, setDownloadProgress] = useState(null);
    const [videoPlayerData, setVideoPlayerData] = useState(null); // { url, title }
    const [homepageContent, setHomepageContent] = useState(null);
    const [homepageLoading, setHomepageLoading] = useState(false);
    const [activeSource, setActiveSource] = useState(() => {
        return localStorage.getItem('moviebox_active_source') || 'moviebox';
    });

    // Update localStorage when activeSource changes
    useEffect(() => {
        localStorage.setItem('moviebox_active_source', activeSource);
        // Clear results when switching sources to avoid mixing
        setResults([]);
        setHomepageContent(null);
    }, [activeSource]);

    // Update localStorage when mode changes
    useEffect(() => {
        localStorage.setItem('moviebox_server_mode', serverMode);
    }, [serverMode]);

    // Fetch homepage content on mount or server/source change
    useEffect(() => {
        const fetchHomepage = async () => {
            if (!API_BASE) return;
            setHomepageLoading(true);
            try {
                const endpoint = activeSource === 'moviebox' ? '/api/homepage' : '/api/anime/home';
                const res = await fetch(`${API_BASE}${endpoint}`);
                if (res.ok) {
                    if (activeSource === 'moviebox') {
                        const data = await res.json();
                        // MovieBox normalization
                        setHomepageContent(data.groups.map(g => ({
                            ...g,
                            items: g.items.map(it => ({
                                ...it,
                                source: 'moviebox' // Explicit source
                            }))
                        })));
                    } else {
                        // HiAnime normalization
                        const data = await res.json();
                        const normalizedGroups = [];
                        if (data.status === 200 && data.data) {
                            const d = data.data;
                            if (d.spotlightAnimes) normalizedGroups.push({ title: 'Spotlight', items: d.spotlightAnimes.map(a => ({ id: a.id, title: a.name, poster_url: a.poster, year: a.type || 'Anime', type: 'anime', source: 'hianime' })) });
                            if (d.trendingAnimes) normalizedGroups.push({ title: 'Trending', items: d.trendingAnimes.map(a => ({ id: a.id, title: a.name, poster_url: a.poster, year: a.type || 'Anime', type: 'anime', source: 'hianime' })) });
                            if (d.latestEpisodeAnimes) normalizedGroups.push({ title: 'Latest Episodes', items: d.latestEpisodeAnimes.map(a => ({ id: a.id, title: a.name, poster_url: a.poster, year: a.type || 'Anime', type: 'anime', source: 'hianime' })) });
                            if (d.topUpcomingAnimes) normalizedGroups.push({ title: 'Upcoming', items: d.topUpcomingAnimes.map(a => ({ id: a.id, title: a.name, poster_url: a.poster, year: a.type || 'Anime', type: 'anime', source: 'hianime' })) });
                        }
                        setHomepageContent(normalizedGroups);
                    }
                }
            } catch (err) {
                console.error("Failed to fetch homepage", err);
            } finally {
                setHomepageLoading(false);
            }
        };

        fetchHomepage();
    }, [API_BASE, activeSource]);

    const toggleServer = () => {
        setServerMode(prev => prev === 'cloud' ? 'local' : 'cloud');
    };

    React.useEffect(() => {
        // WebSocket URL needs to match the current API_BASE
        // Replace http/https with ws/wss
        const wsUrl = API_BASE.replace(/^http/, 'ws') + '/api/ws';

        let ws;
        try {
            ws = new WebSocket(wsUrl);

            ws.onopen = () => {
                console.log('Connected to WebSocket at', wsUrl);
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    console.log('WS Message:', data);
                    if (data.status === 'downloading') {
                        setDownloadProgress(data.progress);
                    } else if (data.status === 'completed') {
                        setDownloadProgress(null);
                        alert('Download Complete!');
                    } else if (data.status === 'error') {
                        setDownloadProgress(null);
                        alert(`Error: ${data.message}`);
                    }
                } catch (e) {
                    console.error('WS Error:', e);
                }
            };
        } catch (err) {
            console.error("WebSocket connection failed", err);
        }

        return () => {
            if (ws) ws.close();
        };
    }, [API_BASE]); // Re-connect when API_BASE changes

    const handleSearch = async (query, type = 'all') => {
        setLoading(true);
        try {
            const endpoint = activeSource === 'moviebox'
                ? `/api/search?query=${encodeURIComponent(query)}&content_type=${type}`
                : `/api/anime/search?query=${encodeURIComponent(query)}`;

            const res = await fetch(`${API_BASE}${endpoint}`);
            const data = await res.json();

            if (activeSource === 'moviebox') {
                setResults(data.results.map(it => ({ ...it, source: 'moviebox' })));
            } else {
                // Normalize HiAnime results
                if (data.status === 200 && data.data && data.data.animes) {
                    const normalized = data.data.animes.map(a => ({
                        id: a.id,
                        title: a.name,
                        poster_url: a.poster,
                        year: a.type || 'Anime',
                        type: 'anime',
                        source: 'hianime'
                    }));
                    setResults(normalized);
                } else {
                    setResults([]);
                }
            }
        } catch (err) {
            console.error("Search failed", err);
            // Detailed error alerting for debugging
            alert(`Connection Failed!\n\nTarget: ${API_BASE}${endpoint}\nError: ${err.message}\n\nPlease ensure the backend is running on Port 8000.`);
        } finally {
            setLoading(false);
        }
    };

    const handleItemClick = async (item) => {
        // Save to Watch History
        try {
            const h = JSON.parse(localStorage.getItem('moviebox_watch_history') || '[]');
            const newH = [item, ...h.filter(x => String(x.id) !== String(item.id))].slice(0, 50);
            localStorage.setItem('moviebox_watch_history', JSON.stringify(newH));
        } catch (e) {
            console.error("Failed to save history", e);
        }

        setDetailsLoading(true);
        try {
            // Unambiguous routing based on source field
            if (item.source === 'moviebox' || !item.source) { // Fallback for items without explicit source
                const res = await fetch(`${API_BASE}/api/details/${item.id}`);
                const details = await res.json();

                // If it's a series, it should have seasons
                setSelectedItem({
                    ...item,
                    ...details,
                    poster_url: details.poster_url || item.poster_url,
                    source: 'moviebox'
                });
            } else {
                // HiAnime Details & Episodes fetch concurrently
                let details = {};
                try {
                    const detailsRes = await fetch(`${API_BASE}/api/anime/details/${item.id}`);
                    if (detailsRes.ok) details = await detailsRes.json();
                } catch (e) { console.error("Details fetch failed", e); }

                let episodes = [];
                try {
                    const episodesRes = await fetch(`${API_BASE}/api/anime/episodes/${item.id}`);
                    const episodesData = await episodesRes.json();
                    if (episodesData.status === 200 && episodesData.data) {
                        episodes = episodesData.data.episodes || [];
                    }
                } catch (e) { console.error("Episodes fetch failed", e); }

                // Merge details into original item to ensure we never lose title/poster
                setSelectedItem({
                    ...item,
                    ...(details.id ? details : {}),
                    animeEpisodes: episodes,
                    type: item.type // Ensure type remains 'anime' or 'anime_movie'
                });
            }
        } catch (err) {
            console.error("Critical failure in handleItemClick", err);
            setSelectedItem(item);
        } finally {
            setDetailsLoading(false);
        }
    };

    const handleDownload = async (item, season = null, episode = null) => {
        try {
            let url = `${API_BASE}/api/download?`;
            if (item.id) {
                url += `id=${encodeURIComponent(item.id)}&`;
            }
            url += `query=${encodeURIComponent(item.title)}`;
            if (season && episode) {
                url += `&season=${season}&episode=${episode}`;
            }

            // Start download in background
            fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            }).catch(err => console.error("Download failed", err));

            // Show brief notification
            alert('Download started');
        } catch (err) {
            console.error("Download failed", err);
            alert("Failed to start download");
        }
    };

    const handleStream = async (item, season = null, episode = null) => {
        console.log("[App] handleStream called for:", item.title, "Ep:", episode);
        setSelectedItem(null);
        setVideoPlayerData({
            item: item,
            season: season,
            episode: episode
        });
    };


    return (
        <div className="app">
            <header className="glass-panel" style={{ position: 'sticky', top: 0, zIndex: 50, padding: '1.5rem 0', marginBottom: '2rem', borderBottom: '1px solid var(--border-glass)', borderTop: 'none', borderLeft: 'none', borderRight: 'none' }}>
                <div className="container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div>
                        <h1 style={{ fontSize: '2rem', margin: 0 }}>GENGA MOVIES</h1>
                        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>Cinematic Discovery</p>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                        {scanningStatus && (
                            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', animation: 'pulse 1.5s infinite' }}>
                                {scanningStatus}
                            </span>
                        )}

                        <button
                            onClick={() => setShowHistoryModal(true)}
                            style={{
                                background: 'transparent',
                                border: 'none',
                                color: 'var(--text-muted)',
                                cursor: 'pointer',
                                padding: '0.5rem',
                                display: 'flex',
                                alignItems: 'center'
                            }}
                            title="Search History"
                        >
                            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <circle cx="12" cy="12" r="10"></circle>
                                <polyline points="12 6 12 12 16 14"></polyline>
                            </svg>
                        </button>

                        <button
                            onClick={() => setShowManualIP(true)}
                            style={{
                                background: 'transparent',
                                border: 'none',
                                color: 'var(--text-muted)',
                                cursor: 'pointer',
                                padding: '0.5rem',
                                display: 'flex',
                                alignItems: 'center'
                            }}
                            title="Configure Server IP"
                        >
                            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <circle cx="12" cy="12" r="3"></circle>
                                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
                            </svg>
                        </button>

                        <div style={{ display: 'flex', background: 'rgba(255, 255, 255, 0.05)', borderRadius: '25px', padding: '4px', border: '1px solid var(--border-glass)' }}>
                            <button
                                onClick={() => setActiveSource('moviebox')}
                                style={{
                                    padding: '0.5rem 1.2rem',
                                    borderRadius: '20px',
                                    border: 'none',
                                    background: activeSource === 'moviebox' ? 'var(--primary)' : 'transparent',
                                    color: activeSource === 'moviebox' ? 'white' : 'var(--text-muted)',
                                    cursor: 'pointer',
                                    fontSize: '0.85rem',
                                    fontWeight: '500',
                                    transition: 'all 0.3s ease'
                                }}
                            >
                                Movie Box
                            </button>
                            <button
                                onClick={() => setActiveSource('hianime')}
                                style={{
                                    padding: '0.5rem 1.2rem',
                                    borderRadius: '20px',
                                    border: 'none',
                                    background: activeSource === 'hianime' ? 'var(--primary)' : 'transparent',
                                    color: activeSource === 'hianime' ? 'white' : 'var(--text-muted)',
                                    cursor: 'pointer',
                                    fontSize: '0.85rem',
                                    fontWeight: '500',
                                    transition: 'all 0.3s ease'
                                }}
                            >
                                HiAnime
                            </button>
                        </div>

                        <button
                            onClick={toggleServer}
                            style={{
                                background: 'rgba(255, 255, 255, 0.1)',
                                border: '1px solid var(--border-glass)',
                                color: 'var(--text-primary)',
                                padding: '0.5rem 1rem',
                                borderRadius: '20px',
                                cursor: 'pointer',
                                fontSize: '0.8rem',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.5rem'
                            }}
                        >
                            <span style={{
                                width: '8px',
                                height: '8px',
                                borderRadius: '50%',
                                background: serverMode === 'cloud' ? '#10b981' : '#f59e0b',
                                display: 'inline-block'
                            }}></span>
                            {serverMode === 'cloud' ? 'Cloud' : 'Local'}
                        </button>
                    </div>
                </div>
            </header>

            <main className="container">
                <SearchBar onSearch={handleSearch} />

                {loading && (
                    <div style={{ textAlign: 'center', padding: '4rem' }}>
                        <div className="spinner" style={{
                            width: '50px', height: '50px',
                            border: '3px solid rgba(255,255,255,0.1)',
                            borderTopColor: 'var(--primary)',
                            borderRadius: '50%',
                            animation: 'spin 1s linear infinite',
                            margin: '0 auto'
                        }}></div>
                        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
                    </div>
                )}

                <div className="movie-card-grid" style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
                    gap: '2rem',
                    paddingBottom: '4rem'
                }}>
                    {results.map((item) => (
                        <MovieCard key={item.id} movie={item} onClick={handleItemClick} />
                    ))}
                </div>

                {results.length === 0 && !loading && (
                    <>
                        {homepageLoading ? (
                            <div style={{ textAlign: 'center', padding: '4rem', color: 'var(--text-muted)' }}>
                                <div className="spinner" style={{
                                    width: '30px', height: '30px',
                                    border: '2px solid rgba(255,255,255,0.1)',
                                    borderTopColor: 'var(--primary)',
                                    borderRadius: '50%',
                                    animation: 'spin 1s linear infinite',
                                    margin: '0 auto 1rem auto'
                                }}></div>
                                Loading trending content...
                            </div>
                        ) : homepageContent ? (
                            <div style={{ paddingBottom: '4rem' }}>
                                {homepageContent.map((group, index) => (
                                    <div key={index} style={{ marginBottom: '3rem' }}>
                                        <h2 style={{
                                            marginBottom: '1.5rem',
                                            paddingLeft: '1rem',
                                            borderLeft: '4px solid var(--primary)',
                                            fontSize: '1.5rem',
                                            fontWeight: '600'
                                        }}>
                                            {group.title}
                                        </h2>
                                        <div className="movie-card-grid" style={{
                                            display: 'grid',
                                            gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
                                            gap: '2rem'
                                        }}>
                                            {group.items.map((item) => (
                                                <MovieCard key={item.id} movie={item} onClick={handleItemClick} />
                                            ))}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div style={{ textAlign: 'center', color: 'var(--text-muted)', marginTop: '4rem', padding: '2rem', border: '1px dashed var(--border-glass)', borderRadius: 'var(--radius-md)' }}>
                                <p style={{ fontSize: '1.2rem' }}>Start by searching for a movie or TV show.</p>
                                <p style={{ fontSize: '0.9rem', marginTop: '1rem', opacity: 0.7 }}>
                                    Connected to: {API_BASE}
                                </p>
                            </div>
                        )}
                    </>
                )}
            </main>

            {
                selectedItem && (
                    <DetailsModal
                        item={selectedItem}
                        onClose={() => setSelectedItem(null)}
                        onDownload={handleDownload}
                        onStream={handleStream}
                        onLanguageChange={(newLanguage) => {
                            // Extract base title and search for new language version
                            const baseTitle = selectedItem.title.replace(/\[.*?\]/g, '').trim();
                            const searchQuery = `${baseTitle} [${newLanguage}]`;
                            setSelectedItem(null); // Close modal
                            handleSearch(searchQuery, selectedItem.type); // Trigger search
                        }}
                        progress={downloadProgress}
                        serverMode={serverMode}
                        API_BASE={API_BASE}
                    />
                )
            }

            {/* In-App Watch Page */}
            {videoPlayerData && (
                <WatchPage
                    item={videoPlayerData.item}
                    initialSeason={videoPlayerData.season}
                    initialEpisode={videoPlayerData.episode}
                    API_BASE={API_BASE}
                    onBack={() => setVideoPlayerData(null)}
                />
            )}

            {
                detailsLoading && (
                    <div className="modal-backdrop">
                        <div className="spinner" style={{
                            width: '50px', height: '50px',
                            border: '3px solid rgba(255,255,255,0.1)',
                            borderTopColor: 'var(--primary)',
                            borderRadius: '50%',
                            animation: 'spin 1s linear infinite'
                        }}></div>
                    </div>
                )
            }

            {/* Manual IP Configuration Modal */}
            {showManualIP && (
                <div className="modal-backdrop" onClick={() => setShowManualIP(false)}>
                    <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: '400px', padding: '2rem' }}>
                        <h3 style={{ marginTop: 0 }}>Configure Server IP</h3>
                        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1.5rem' }}>
                            If auto-detection fails, enter your computer's local IP address manually.
                            (e.g., 192.168.31.232)
                        </p>

                        <div style={{ marginBottom: '1.5rem' }}>
                            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem' }}>Server IP Address</label>
                            <input
                                type="text"
                                className="input-glass"
                                placeholder="192.168.x.x:8000 or :8080"
                                value={manualIPInput}
                                onChange={(e) => setManualIPInput(e.target.value)}
                                style={{ width: '100%', padding: '0.8rem' }}
                            />
                        </div>

                        <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
                            <button
                                className="btn"
                                onClick={() => setShowManualIP(false)}
                                style={{ background: 'transparent', border: '1px solid var(--border-glass)' }}
                            >
                                Cancel
                            </button>
                            <button
                                className="btn btn-primary"
                                onClick={() => {
                                    if (manualIPInput) {
                                        let url = manualIPInput.trim();

                                        // Add http:// if missing
                                        if (!url.startsWith('http')) {
                                            url = 'http://' + url;
                                        }

                                        // Helper to find correct port
                                        const findBackendPort = async (baseUrl) => {
                                            const ip = baseUrl.split('://')[1].split(':')[0];

                                            const check = async (port) => {
                                                const controller = new AbortController();
                                                const id = setTimeout(() => controller.abort(), 1000);
                                                try {
                                                    const res = await fetch(`http://${ip}:${port}/api/health`, { signal: controller.signal });
                                                    clearTimeout(id);
                                                    if (res.ok) return `http://${ip}:${port}`;
                                                } catch (e) { }
                                                return null;
                                            };

                                            const port8080 = await check(8080);
                                            if (port8080) return port8080;

                                            const port8000 = await check(8000);
                                            if (port8000) return port8000;

                                            return null;
                                        };

                                        // Common handler for setting found URL
                                        const setFoundUrl = (targetUrl) => {
                                            if (targetUrl.endsWith('/')) targetUrl = targetUrl.slice(0, -1);

                                            setLocalServerURL(targetUrl);
                                            BACKENDS.local = targetUrl;
                                            localStorage.setItem('moviebox_local_ip', targetUrl);
                                            setServerMode('local');
                                            setShowManualIP(false);

                                            // Test connection
                                            fetch(`${targetUrl}/api/health`)
                                                .then(res => {
                                                    if (res.ok) alert(`Successfully connected to ${targetUrl}`);
                                                    else alert(`Connected to ${targetUrl} but health check failed.`);
                                                })
                                                .catch(() => alert(`Connected to ${targetUrl} but unreachable.`));
                                        };

                                        // Handle Frontend Port (5173) copy-paste
                                        if (url.includes(':5173')) {
                                            findBackendPort(url).then(foundUrl => {
                                                if (foundUrl) {
                                                    setFoundUrl(foundUrl);
                                                } else {
                                                    // Fallback to 8080 if detection fails
                                                    const fallback = url.replace(':5173', ':8080');
                                                    setFoundUrl(fallback);
                                                }
                                            });
                                            return;
                                        }

                                        // If no port specified
                                        else if ((url.match(/:/g) || []).length < 2) {
                                            findBackendPort(url).then(foundUrl => {
                                                setFoundUrl(foundUrl || (url + ':8080'));
                                            });
                                            return;
                                        }

                                        // Explicit port entered - just use it
                                        setFoundUrl(url);

                                        // Test connection immediately
                                        fetch(`${url}/api/health`)
                                            .then(res => {
                                                if (res.ok) alert(`Successfully connected to ${url}`);
                                                else throw new Error(res.statusText);
                                            })
                                            .catch(err => {
                                                alert(`Saved ${url}, but connection failed: ${err.message}. \n\nCheck Windows Firewall!`);
                                            });
                                    }
                                }}
                            >
                                Save & Connect
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Watch History Modal */}
            {showHistoryModal && (
                <div className="modal-backdrop" onClick={() => setShowHistoryModal(false)}>
                    <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: '500px', padding: '2rem', maxHeight: '80vh', display: 'flex', flexDirection: 'column' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexShrink: 0 }}>
                            <h3 style={{ margin: 0 }}>History</h3>
                            <button onClick={() => { localStorage.removeItem('moviebox_watch_history'); setShowHistoryModal(false); }} style={{ background: 'transparent', border: 'none', color: '#ef4444', cursor: 'pointer', fontSize: '0.9rem' }}>Clear All</button>
                        </div>

                        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', overflowY: 'auto', paddingRight: '5px', flex: 1 }}>
                            {(() => {
                                try {
                                    const h = JSON.parse(localStorage.getItem('moviebox_watch_history') || '[]');
                                    if (h.length === 0) return <p style={{ color: 'var(--text-muted)', textAlign: 'center', margin: '2rem 0' }}>No history yet.</p>;
                                    return h.slice(0, 50).map((item, idx) => (
                                        <div
                                            key={idx}
                                            onClick={() => {
                                                handleItemClick(item);
                                                setShowHistoryModal(false);
                                            }}
                                            style={{
                                                display: 'flex',
                                                gap: '15px',
                                                cursor: 'pointer',
                                                background: 'rgba(255,255,255,0.02)',
                                                borderRadius: '8px',
                                                padding: '10px',
                                                transition: 'background 0.2s',
                                                position: 'relative',
                                                border: '1px solid transparent'
                                            }}
                                            onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.05)'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)'; }}
                                            onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.02)'; e.currentTarget.style.borderColor = 'transparent'; }}
                                        >
                                            <div style={{ width: '80px', height: '120px', flexShrink: 0, borderRadius: '6px', overflow: 'hidden', background: '#222' }}>
                                                {item.poster_url ? (
                                                    <img src={item.poster_url} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                                                ) : (
                                                    <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#555' }}>No Img</div>
                                                )}
                                            </div>
                                            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                                                <h4 style={{ margin: '0 0 6px 0', fontSize: '1rem', lineHeight: '1.3' }}>{item.title}</h4>
                                                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'inline-block', background: 'rgba(255,255,255,0.1)', padding: '2px 6px', borderRadius: '4px', alignSelf: 'flex-start' }}>
                                                    {item.year || (item.type === 'anime' ? 'Anime' : 'Movie/TV')}
                                                </span>
                                            </div>
                                        </div>
                                    ));
                                } catch (e) { return null; }
                            })()}
                        </div>

                        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '1.5rem', flexShrink: 0 }}>
                            <button
                                className="btn"
                                onClick={() => setShowHistoryModal(false)}
                                style={{ background: 'transparent', border: '1px solid var(--border-glass)' }}
                            >
                                Close
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export default App;
