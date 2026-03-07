import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import SearchBar from './components/SearchBar';
import MovieCard from './components/MovieCard';
import DetailsModal from './components/DetailsModal';
import WatchPage from './components/WatchPage';
import MangaReader from './components/MangaReader';
import Sidebar from './components/Sidebar';
import MusicCard from './components/MusicCard';
import MusicPlayer from './components/MusicPlayer';
import NewsCard from './components/NewsCard';
import NewsReader from './components/NewsReader';
import NovelReader from './components/NovelReader';
import './styles/index.css';

// Auto-detect local server IP
const detectLocalServer = async (onProgress) => {
    // Check relative path first (for Cloudflare Tunnels / Proxy)
    try {
        const res = await fetch('/api/health');
        if (res.ok) {
            console.log('Found backend on relative path');
            return ''; // Empty string for relative path
        }
    } catch (e) {
        // Ignore
    }

    // Check specific IP and port
    const checkIP = async (ip, port = 8000) => {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 500); // 500ms timeout

            // If checking localhost/IP, use http.
            // If checking a domain (tunnel), we might need https, but here we scan local network so http is fine usually.
            // But if 'ip' is actually a hostname, act smart.
            let protocol = 'http';
            if (window.location.protocol === 'https:' && ip !== 'localhost' && !ip.match(/^\d+\./)) {
                protocol = 'https';
            }

            const response = await fetch(`${protocol}://${ip}:${port}/api/health`, {
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
    const hostname = window.location.hostname; // Define hostname here
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
const CLOUD_BASE = 'https://moviebox-knh8.onrender.com';


function App() {
    // State for local server configuration

    const [localServerURL, setLocalServerURL] = useState(() => {
        const saved = localStorage.getItem('moviebox_local_ip');
        return saved !== null ? saved : 'http://localhost:8000';
    });

    const [scanningStatus, setScanningStatus] = useState('');
    const [showManualIP, setShowManualIP] = useState(false);
    const [showHistoryModal, setShowHistoryModal] = useState(false);
    const [historyFilter, setHistoryFilter] = useState('all');
    const [historyItems, setHistoryItems] = useState(() => {
        try {
            return JSON.parse(localStorage.getItem('moviebox_watch_history') || '[]');
        } catch (e) {
            return [];
        }
    });
    const [manualIPInput, setManualIPInput] = useState('');
    const [activeSource, setActiveSource] = useState(() => {
        // Default to 'home' which aggregates or shows default homepage
        return localStorage.getItem('moviebox_active_source') || 'home';
    });

    // Update localStorage when activeSource changes
    useEffect(() => {
        localStorage.setItem('moviebox_active_source', activeSource);
        // Clear results when switching sources to avoid mixing
        setResults([]);

        // If switching to home, we typically want to clear search and show aggregation
        // If switching to a specific source, we might auto-fetch its specific homepage variant
        setHomepageContent(null);

    }, [activeSource]);

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

                setScanningStatus('');
                if (url !== 'http://localhost:8000') {
                    localStorage.setItem('moviebox_local_ip', url);
                }
            });
        } else {

        }
    }, []);

    // Helper to determine target base URL for a given source
    const getTargetBase = (src = activeSource) => {
        return (src === 'hianime' || src === 'manga' || src === 'anicli' || src === 'music' || src === 'news')
            ? CLOUD_BASE
            : localServerURL;
    };

    const API_BASE = getTargetBase(activeSource);

    const [results, setResults] = useState([]);
    const [loading, setLoading] = useState(false);
    const [selectedItem, setSelectedItem] = useState(null); // For DetailsModal
    const [videoPlayerData, setVideoPlayerData] = useState(null); // For WatchPage
    const [mangaReaderItem, setMangaReaderItem] = useState(null); // For MangaReader
    const [activeTrack, setActiveTrack] = useState(null); // For MusicPlayer
    const [detailsLoading, setDetailsLoading] = useState(false);
    const [newsReaderItem, setNewsReaderItem] = useState(null);
    const [downloadProgress, setDownloadProgress] = useState(null);
    const [homepageContent, setHomepageContent] = useState(null);
    const [homepageLoading, setHomepageLoading] = useState(false);
    const [novelReaderItem, setNovelReaderItem] = useState(null);

    // Server status (simple polling or just static 'operational' for now, can be updated by backend)
    const [serverStatus, setServerStatus] = useState('operational');


    useEffect(() => {
        // Just a simple status check simulation
        setServerStatus('operational');

        const fetchHomepage = async () => {
            if (API_BASE === null) return;

            // Don't fetch homepage if we are in 'cinecli' or search mode (unless implemented)
            if (activeSource === 'cinecli') {
                setHomepageContent([]); // Placeholder for CineCLI home
                return;
            }

            setHomepageLoading(true);
            try {
                // Determine endpoint based on source
                // 'home' -> defaults to moviebox for now, or we could mix
                // 'moviebox' -> /api/homepage
                // 'hianime' -> /api/anime/home

                let endpoint = '/api/homepage';
                if (activeSource === 'hianime') endpoint = '/api/anime/home';
                if (activeSource === 'manga') endpoint = '/api/manga/search?query=popular';
                if (activeSource === 'novel') endpoint = '/api/novel/search?query=trending';
                if (activeSource === 'music') endpoint = '/api/music/home';
                if (activeSource === 'news') {
                    // Fetch from Consumet News API directly for now
                    const newsRes = await fetch('https://api-consumet-org-mswp.onrender.com/news/ann/recent-feeds');
                    if (newsRes.ok) {
                        const newsData = await newsRes.json();
                        setHomepageContent([{ title: 'Latest Anime & Manga News', items: newsData, type: 'news' }]);
                        setHomepageLoading(false);
                        return;
                    }
                }

                const res = await fetch(`${API_BASE}${endpoint}`);
                if (res.ok) {
                    if (activeSource === 'moviebox' || activeSource === 'home') {
                        const data = await res.json();
                        // MovieBox normalization
                        setHomepageContent(data.groups.map(g => ({
                            ...g,
                            items: g.items.map(it => ({
                                ...it,
                                source: 'moviebox' // Explicit source
                            }))
                        })));
                    } else if (activeSource === 'hianime') {
                        // HiAnime normalization now handled by backend
                        const data = await res.json();
                        setHomepageContent(data);
                    } else if (activeSource === 'manga') {
                        // Manga normalization
                        const data = await res.json();
                        const results = data.results || [];
                        setHomepageContent([{
                            title: 'Popular Manga',
                            items: results.map(it => ({
                                ...it,
                                source: 'manga',
                                poster_url: `${API_BASE}/api/manga/image-proxy?url=${encodeURIComponent(it.poster_url)}`
                            }))
                        }]);
                    } else if (activeSource === 'novel') {
                        // Novel section: don't hammer the crawler API for a homepage.
                        // Set a special marker so the empty state renders nicely.
                        setHomepageContent([{
                            title: 'Novel Library',
                            items: [],
                            _novelWelcome: true,
                        }]);
                        setHomepageLoading(false);
                        return;

                    } else if (activeSource === 'music') {
                        const data = await res.json();
                        // Backend returns { "groups": [...] }
                        if (data.groups) {
                            setHomepageContent(data.groups);
                        }
                    }
                }
            } catch (err) {
                console.error("Failed to fetch homepage", err);
                setHomepageContent([]); // Clear homepage content on error
            } finally {
                setHomepageLoading(false);
            }
        };

        // Added this simple check to prevent infinity loop if activeSource doesn't change
        // Only fetch if homepageContent is null (when changing sources it's set to null)
        if (homepageContent === null) {
            fetchHomepage();
        }

    }, [API_BASE, activeSource, homepageContent]);



    React.useEffect(() => {
        // WebSocket URL needs to match the current API_BASE
        // Replace http/https with ws/wss
        const wsUrl = API_BASE
            ? API_BASE.replace(/^http/, 'ws') + '/api/ws'
            : (window.location.protocol === 'https:' ? 'wss://' : 'ws://') + window.location.host + '/api/ws';

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
            // Determine endpoint based on activeSource
            // 'home' -> searches moviebox by default or we could aggregate (stick to moviebox for now)
            // 'cinecli' -> Not implemented yet in backend, but we'll prepare for it

            let endpoint = `/api/search?query=${encodeURIComponent(query)}&content_type=${type}`;
            const base = getTargetBase(activeSource);

            if (activeSource === 'hianime') {
                endpoint = `/api/anime/search?query=${encodeURIComponent(query)}`;
            } else if (activeSource === 'cinecli') {
                endpoint = `/api/cinecli/search?query=${encodeURIComponent(query)}`;
            } else if (activeSource === 'manga') {
                endpoint = `/api/manga/search?query=${encodeURIComponent(query)}`;
            } else if (activeSource === 'music') { // Added music search logic
                endpoint = `/api/music/search?query=${encodeURIComponent(query)}`;
            } else if (activeSource === 'novel') {
                endpoint = `/api/novel/search?query=${encodeURIComponent(query)}`;
            }

            const res = await fetch(`${base}${endpoint}`);
            const data = await res.json();

            if (activeSource === 'hianime') {
                // Backend already normalizes anime results
                setResults(Array.isArray(data) ? data : []);
            } else if (activeSource === 'manga') {
                setResults(data.results.map(it => ({
                    ...it,
                    source: 'manga',
                    poster_url: `${base}/api/manga/image-proxy?url=${encodeURIComponent(it.poster_url)}`
                })));
            } else if (activeSource === 'music') { // Added music search normalization
                setResults(data.results || []);
            } else if (activeSource === 'novel') {
                setResults(data.results || []);
            } else {
                // MovieBox results: SubjectType 1=Movie, 2=Series
                setResults(data.results.map(it => {
                    let determinedType = it.type;
                    if (typeof it.type !== 'string') {
                        determinedType = it.type === 2 ? 'series' : 'movie';
                    }
                    return { ...it, source: 'moviebox', type: determinedType };
                }));
            }
        } catch (err) {
            console.error("Search failed", err);
            // Detailed error alerting with Cold Start explanation
            const isColdStart = err.message === 'Failed to fetch' || err.message.includes('timeout');
            const coldStartMsg = isColdStart ? "\n\nNote: This might be a 'Cold Start'. Render servers sleep after inactivity. Please wait 30 seconds and try again." : "";
            alert(`Connection Failed!\n\nError: ${err.message}${coldStartMsg}\n\nPlease ensure your backend is reachable.`);
        } finally {
            setLoading(false);
        }
    };

    const handleMusicPlay = async (item) => {
        setDetailsLoading(true);
        try {
            const base = getTargetBase(activeSource);
            const res = await fetch(`${base}/api/music/info?seokey=${item.id}&type=${item.type || 'music'}`);
            const data = await res.json();

            let trackToPlay = data;
            if (item.type === 'music_playlist') {
                const tracks = data.tracks || (Array.isArray(data) ? data : []);
                if (tracks.length > 0) {
                    trackToPlay = tracks[0];
                    // Add source info if missing
                    if (!trackToPlay.source) trackToPlay.source = 'music';
                }
            }

            if (trackToPlay && trackToPlay.stream_url) {
                setActiveTrack(trackToPlay);
                setSelectedItem(null); // Close modal if open
            } else {
                alert("Could not play this track. Stream URL missing.");
            }
        } catch (e) {
            console.error("Failed to play music", e);
        } finally {
            setDetailsLoading(false);
        }
    };

    const handleItemClick = async (item) => {
        // Save to Watch History
        try {
            const h = JSON.parse(localStorage.getItem('moviebox_watch_history') || '[]');
            const newH = [item, ...h.filter(x => String(x.id) !== String(item.id))];
            localStorage.setItem('moviebox_watch_history', JSON.stringify(newH));
            setHistoryItems(newH);
        } catch (e) {
            console.error("Failed to save history", e);
        }

        const src = item.source || 'moviebox';
        // Set selected item immediately to preserve poster/metadata for the modal
        setSelectedItem({ ...item, source: src });

        // If it's a music item, handle based on type
        if (item.source === 'music' || item.type === 'music' || item.type === 'music_playlist') {
            if (item.type === 'music_playlist') {
                // For playlists, open details modal to select track
                navigate(`/details/${item.id}?source=music&type=music_playlist`);
            } else {
                // For single tracks, play directly
                handleMusicPlay(item);
            }
            return;
        }

        // Ensure we show loading state if details are missing (e.g. from History)
        const isComplete = (it) => {
            if (!it || !it.hasFullDetails) return false;
            const s = it.source || src;
            if (s === 'hianime') return it.animeEpisodes && it.animeEpisodes.length > 0;
            if (s === 'manga') return it.volumes && Object.keys(it.volumes).length > 0;
            if (s === 'novel') return it.volumes && Object.keys(it.volumes).length > 0;
            if (it.type === 'series' || it.type === 'anime') return it.seasons && it.seasons.length > 0;
            return !!(it.plot || it.description);
        };

        if (!isComplete(item)) {
            setDetailsLoading(true);
        }

        // Encode ID for novel source since it might be a full URL
        const encodedId = src === 'novel' ? encodeURIComponent(item.id) : item.id;

        // Navigate to details route; router will load remaining details (like chapters/episodes)
        navigate(`/details/${encodedId}?source=${encodeURIComponent(src)}&type=${item.type || 'movie'}`);
    };

    const handleDownload = async (item, season = null, episode = null, url = null) => {
        // If we already have a direct URL (e.g. from CineCLI magnet or explicit file)
        if (url) {
            window.location.href = url;
            return;
        }

        // For Music items
        if (item.source === 'music') {
            try {
                const base = getTargetBase(activeSource);
                const res = await fetch(`${base}/api/music/info?seokey=${item.id}&type=${item.type || 'music'}`);
                const data = await res.json();
                let track = data;
                if (item.type === 'music_playlist' && data.tracks) track = data.tracks[0];

                if (track && track.stream_url) {
                    const proxyUrl = `${base}/api/proxy/download?url=${encodeURIComponent(track.stream_url)}&filename=${encodeURIComponent(track.title + (track.stream_url.includes('.m3u8') ? '.m3u8' : '.mp3'))}`;
                    window.location.href = proxyUrl;
                }
            } catch (err) {
                console.error("Music download failed", err);
            }
            return;
        }

        // For MovieBox items, we need to resolve the stream URL first
        try {
            // 1. Fetch the stream URL from backend
            // Determine appropriate base URL for this specific item
            const base = getTargetBase(item.source);

            // Let's try to fetch details which usually contains 'streams' or 'sources'.
            const res = await fetch(`${base}/api/details/${item.id}?type=${item.type || 'movie'}`);
            const data = await res.json();

            let streamUrl = null;
            if (data.streams && data.streams.length > 0) {
                streamUrl = data.streams[0].url;
            } else if (data.sources && data.sources.length > 0) {
                streamUrl = data.sources[0].url;
            }

            if (streamUrl) {
                // 2. Redirect to Proxy Download
                const proxyUrl = `${base}/api/proxy/download?url=${encodeURIComponent(streamUrl)}&filename=${encodeURIComponent(item.title + '.mp4')}`;
                window.location.href = proxyUrl;
            } else {
                alert("Could not resolve a download link for this item.");
            }

        } catch (err) {
            console.error("Download resolution failed", err);
            alert("Failed to start download");
        }
    };

    const handleStream = async (item, season = null, episode = null) => {
        if (item.source === 'music' || item.type === 'music' || item.type === 'music_playlist') {
            handleMusicPlay(item);
            return;
        }

        if (item.type === 'manga') {
            setMangaReaderItem({ item, chapterId: item.chapterId, chapterTitle: item.chapterTitle });
            // Do not clear selectedItem, so we can go back to it
            return;
        }

        if (item.type === 'novel') {
            const encodedId = encodeURIComponent(item.id);
            setNovelReaderItem({ item, chapterId: item.chapterId, chapterTitle: item.chapterTitle });
            // Do not clear selectedItem, so we can go back to it
            return;
        }

        console.log("[App] handleStream called for:", item && item.title, "Ep arg:", episode, "itemEp:", item && (item.episodeNo || item.episodeId || item.episode));

        // Determine episode value from explicit arg or from item payload (HiAnime uses episodeNo/episodeId)
        let epValue = null;
        if (episode !== null && episode !== undefined) epValue = episode;
        else if (item && (item.episodeNo !== undefined && item.episodeNo !== null)) epValue = item.episodeNo;
        else if (item && (item.episode !== undefined && item.episode !== null)) epValue = item.episode;

        const src = (item && item.source) ? item.source : 'moviebox';

        // Pre-populate watchItem so the Watch UI appears immediately (avoid flashing Home)
        const preload = {
            item: { ...item, source: src },
            season: season || null,
            episode: epValue || null,
            animeEpisodes: item && item.animeEpisodes ? item.animeEpisodes : null
        };
        setVideoPlayerData(preload);

        // Navigate to watch route with episode and source params
        const params = new URLSearchParams();
        if (epValue !== null && epValue !== undefined) params.set('episode', String(epValue));
        if (season !== null && season !== undefined) params.set('season', String(season));
        params.set('source', src);
        navigate(`/watch/${item.id}?${params.toString()}`);

        // Close the modal after navigation to avoid onClose navigations interfering
        setSelectedItem(null);
    };


    const handleRemoveHistoryItem = (e, id) => {
        e.stopPropagation();
        try {
            const newH = historyItems.filter(x => String(x.id) !== String(id));
            localStorage.setItem('moviebox_watch_history', JSON.stringify(newH));
            setHistoryItems(newH);
        } catch (err) {
            console.error("Failed to remove history item", err);
        }
    };

    const [isSidebarOpen, setIsSidebarOpen] = useState(true);

    const navigate = useNavigate();
    const location = useLocation();

    useEffect(() => {
        // Keep UI in sync with React Router location
        const pathname = location.pathname || '/';
        const search = location.search || '';

        const loadDetails = async (id, source, type = 'movie') => {
            // If loadDetails is called, it means we definitely need to fetch more data.
            // We set detailsLoading(true) to show the prominent spinner.
            setDetailsLoading(true);

            // Determine appropriate base URL for this source
            const base = getTargetBase(source);

            try {
                if (source === 'cinecli') {
                    const res = await fetch(`${base}/api/cinecli/details/${id}`);
                    const details = await res.json();
                    setSelectedItem(prev => ({ ...prev, ...details, source: 'cinecli', hasFullDetails: true }));
                } else if (source === 'anicli') {
                    const res = await fetch(`${base}/api/anicli/details/${id}`);
                    const details = await res.json();
                    setSelectedItem(prev => ({ ...prev, ...details, source: 'anicli', type: 'anime', hasFullDetails: true }));
                } else if (source === 'hianime') {
                    let details = {};
                    let episodes = [];
                    try {
                        const dTask = fetch(`${base}/api/anime/details/${id}`).then(r => r.ok ? r.json() : {});
                        const eTask = fetch(`${base}/api/anime/episodes/${id}`).then(r => r.ok ? r.json() : {});
                        const [d, e] = await Promise.all([dTask, eTask]);
                        details = d;
                        if (e.status === 200 && e.data) episodes = e.data.episodes || [];
                    } catch (e) { /* ignore */ }

                    setSelectedItem(prev => ({
                        ...prev,
                        ...(details.id ? details : { id, title: details.title || (prev && prev.title) || '' }),
                        animeEpisodes: episodes,
                        type: 'anime',
                        source: 'hianime',
                        hasFullDetails: true
                    }));
                } else if (source === 'manga') {
                    const res = await fetch(`${base}/api/manga/details/${id}`);
                    const details = await res.json();
                    setSelectedItem(prev => {
                        const rawPoster = details.poster_url || details.poster || details.image;
                        let finalPoster = prev?.poster_url || null;

                        if (rawPoster && typeof rawPoster === 'string') {
                            if (rawPoster.includes('/api/manga/image-proxy')) {
                                finalPoster = rawPoster;
                            } else if (rawPoster.startsWith('http') || rawPoster.startsWith('//')) {
                                const fullUrl = rawPoster.startsWith('//') ? `https:${rawPoster}` : rawPoster;
                                finalPoster = `${base}/api/manga/image-proxy?url=${encodeURIComponent(fullUrl)}`;
                            } else {
                                finalPoster = rawPoster;
                            }
                        }

                        return {
                            ...(prev || {}),
                            ...details,
                            source: 'manga',
                            type: 'manga',
                            poster_url: finalPoster || prev?.poster_url,
                            hasFullDetails: true
                        };
                    });
                } else if (source === 'novel') {
                    // ID might be encoded URL here, but fetch() handles URL-as-id if backend supports it
                    // The backend handles id.startswith("http") -> treats it as URL
                    const res = await fetch(`${base}/api/novel/info?id=${encodeURIComponent(id)}`);
                    const details = await res.json();
                    setSelectedItem(prev => ({
                        ...prev,
                        ...details,
                        source: 'novel',
                        type: 'novel',
                        hasFullDetails: true
                    }));
                } else if (source === 'music') {
                    const res = await fetch(`${base}/api/music/info?seokey=${id}&type=${type}`);
                    const details = await res.json();
                    setSelectedItem(prev => ({
                        ...prev,
                        ...details,
                        source: 'music',
                        type: type || 'music',
                        hasFullDetails: true
                    }));
                } else {
                    const res = await fetch(`${base}/api/details/${id}?type=${type}`);
                    const details = await res.json();
                    setSelectedItem(prev => ({ ...prev, ...details, source: 'moviebox', hasFullDetails: true }));
                }
            } catch (e) {
                console.error('Failed to load details for route', e);
            } finally {
                setDetailsLoading(false);
            }
        };

        const loadWatch = async (id, ep, source = 'moviebox', season = null) => {
            try {
                let details = { id, source }; // Default with known info
                if (source === 'hianime') {
                    // HiAnime: fetch details and episodes then set player to use embed flow
                    const base = getTargetBase(source);
                    try {
                        const dRes = await fetch(`${base}/api/anime/details/${id}`);
                        if (dRes.ok) details = await dRes.json();
                    } catch (e) { /* ignore */ }

                    let episodes = [];
                    try {
                        const eRes = await fetch(`${base}/api/anime/episodes/${id}`);
                        const eData = await eRes.json();
                        if (eData.status === 200 && eData.data) episodes = eData.data.episodes || [];
                    } catch (e) { /* ignore */ }

                    // Provide enough info for WatchPage to construct embed URL / episodeId mapping
                    const item = { ...details, id, source: 'hianime', type: 'anime', hasFullDetails: true };
                    setVideoPlayerData({ item, season: season || null, episode: ep || null, animeEpisodes: episodes });
                    setSelectedItem(null);
                    return;
                }

                // Default MovieBox flow
                const base = getTargetBase(source);
                const res = await fetch(`${base}/api/details/${id}`);
                if (res.ok) {
                    const d = await res.json();
                    const item = { ...d, id, source, type: (d.type || (source === 'anicli' ? 'anime' : 'movie')), hasFullDetails: true };
                    setVideoPlayerData({ item, season: season || null, episode: ep || null });
                    setSelectedItem(null);
                } else {
                    setVideoPlayerData({ item: { id, source, type: (source === 'anicli' ? 'anime' : 'movie') }, season: season || null, episode: ep || null });
                }
            } catch (e) {
                setVideoPlayerData({ item: { id, source, type: (source === 'anicli' ? 'anime' : 'movie') }, season: season || null, episode: ep || null });
            }
        };

        // Route handling
        if (pathname === '/' || pathname === '') {
            setSelectedItem(null);
            setVideoPlayerData(null);
            setMangaReaderItem(null);
            setNewsReaderItem(null); // Clear NewsReader item
            return;
        }

        if (pathname.startsWith('/details/')) {
            const rawId = pathname.replace('/details/', '').split('?')[0];
            const id = decodeURIComponent(rawId);
            const params = new URLSearchParams(search);
            const source = params.get('source') || 'moviebox';
            const type = params.get('type') || 'movie';

            // Sync activeSource state if it differs from the URL (handles deep-linking)
            if (source !== activeSource && source !== 'home' && activeSource !== 'history') {
                setActiveSource(source);
            }

            let effectiveItem = selectedItem;

            // First check if it's already in active state (e.g. from Reader/Player)
            if (videoPlayerData && String(videoPlayerData.item.id) === String(id)) {
                setSelectedItem(videoPlayerData.item);
                effectiveItem = videoPlayerData.item;
            } else if (mangaReaderItem && String(mangaReaderItem.item.id) === String(id)) {
                setSelectedItem(mangaReaderItem.item);
                effectiveItem = mangaReaderItem.item;
            }

            // Ensure other main views are cleared when viewing details
            if (videoPlayerData) setVideoPlayerData(null);
            if (mangaReaderItem) setMangaReaderItem(null);
            if (newsReaderItem) setNewsReaderItem(null); // Clear NewsReader item

            // Determine if the item is "full enough" for the requested ID
            const isFullItem = (it) => {
                if (!it || String(it.id) !== String(id)) return false;
                if (!it.hasFullDetails) return false;

                // Source-specific checks to ensure we don't show "information not available"
                if (source === 'hianime') return it.animeEpisodes && it.animeEpisodes.length > 0;
                if (source === 'manga') return it.volumes && Object.keys(it.volumes).length > 0;
                if (source === 'music') return (it.tracks && it.tracks.length > 0) || (it.songs && it.songs.length > 0);
                if (it.type === 'series' || it.type === 'anime') return it.seasons && it.seasons.length > 0;

                // For movies, just check for a plot/description
                return !!(it.plot || it.description || (source === 'manga' && it.poster_url));
            };

            if (!isFullItem(effectiveItem)) {
                loadDetails(id, source, type);
            }
            return;
        }

        if (pathname.startsWith('/watch/')) {
            const id = pathname.replace('/watch/', '').split('/')[0];
            const params = new URLSearchParams(search);
            const ep = params.get('episode');
            const season = params.get('season');
            const source = params.get('source') || 'moviebox';

            // Sync activeSource state if it differs from the URL (handles deep-linking)
            if (source !== activeSource && source !== 'home' && activeSource !== 'history') {
                setActiveSource(source);
            }

            loadWatch(id, ep, source, season);
            return;
        }
    }, [location, API_BASE]);

    return (
        <div className="app" style={{ display: 'flex', flexDirection: 'row', maxWidth: '100vw', overflow: 'hidden' }}>

            {/* NEW SIDEBAR */}
            <Sidebar
                activeSource={activeSource}
                onChangeSource={setActiveSource}
                serverStatus={serverStatus}
                isOpen={isSidebarOpen}
                onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
            />

            {/* MAIN CONTENT AREA */}
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100vh', overflowY: 'auto', position: 'relative' }}>

                {/* Header Controls */}
                <div style={{
                    display: 'flex',
                    justifyContent: 'flex-end',
                    gap: '1rem',
                    alignItems: 'center',
                    padding: '1rem 2rem',
                    width: '100%',
                    zIndex: 10
                }}>
                    {scanningStatus && (
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', animation: 'pulse 1.5s infinite', background: 'rgba(0,0,0,0.5)', padding: '4px 8px', borderRadius: '4px' }}>
                            {scanningStatus}
                        </span>
                    )}


                    {(activeSource === 'moviebox' || activeSource === 'home') && (
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
                            title="Configure IP"
                        >
                            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <circle cx="12" cy="12" r="3"></circle>
                                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
                            </svg>
                        </button>
                    )}

                </div>


                <main className="container" style={{ paddingTop: '1rem' }}>

                    {/* Source Title Helper */}
                    <div style={{ marginBottom: '1rem', marginLeft: '0.5rem', opacity: 0.6, fontSize: '0.9rem', textTransform: 'uppercase', letterSpacing: '1px' }}>
                        {activeSource === 'home' ? 'Discover' :
                            activeSource === 'moviebox' ? 'Library' :
                                activeSource === 'hianime' ? 'Anime World' :
                                    activeSource === 'manga' ? 'Manga Collection' :
                                        activeSource === 'music' ? 'Music Library' :
                                            activeSource === 'news' ? 'News Feed' :
                                                activeSource === 'novel' ? 'Novel Library' :
                                                    activeSource === 'history' ? 'Watch History' : 'Genga Movies'}

                    </div>

                    {/* Top Bar with Search */}
                    {activeSource !== 'history' && activeSource !== 'news' && (
                        <div style={{
                            marginBottom: '2rem',
                            display: 'flex',
                            gap: '12px',
                            alignItems: 'center',
                            position: 'sticky',
                            top: '1rem',
                            zIndex: 10,
                            padding: '0.5rem',
                            background: 'rgba(var(--bg-card-rgb), 0.6)',
                            backdropFilter: 'blur(12px)',
                            borderRadius: '20px',
                            border: '1px solid var(--border-glass)',
                            width: '100%',
                            maxWidth: '1200px',
                            margin: '0 auto 2rem'
                        }}>
                            <SearchBar
                                onSearch={handleSearch}
                                placeholder={
                                    activeSource === 'music' ? 'Search music or playlists...' :
                                        activeSource === 'manga' ? "Search manga..." :
                                            activeSource === 'novel' ? "Search novels..." :
                                                activeSource === 'hianime' ? "Search anime..." :
                                                    'Search for movies or series...'}

                            />
                        </div>
                    )}

                    {activeSource === 'history' && (
                        <div style={{ padding: '1rem 0' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                                <div style={{ display: 'flex', gap: '0.5rem' }}>
                                    {['all', 'moviebox', 'hianime', 'manga', 'music'].map(f => (
                                        <button
                                            key={f}
                                            onClick={() => setHistoryFilter(f)}
                                            style={{
                                                padding: '0.5rem 1.2rem',
                                                borderRadius: '20px',
                                                border: '1px solid var(--border-glass)',
                                                background: historyFilter === f ? 'var(--primary)' : 'rgba(255,255,255,0.05)',
                                                color: historyFilter === f ? '#fff' : 'var(--text-muted)',
                                                cursor: 'pointer',
                                                fontSize: '0.85rem',
                                                textTransform: 'capitalize',
                                                transition: 'all 0.2s'
                                            }}
                                        >
                                            {f === 'hianime' ? 'Anime' : f}
                                        </button>
                                    ))}
                                </div>
                                <button
                                    onClick={() => {
                                        if (window.confirm("Are you sure you want to clear your entire history?")) {
                                            localStorage.removeItem('moviebox_watch_history');
                                            window.location.reload();
                                        }
                                    }}
                                    style={{ background: 'transparent', border: 'none', color: '#ef4444', cursor: 'pointer', fontSize: '0.9rem' }}
                                >
                                    Clear All
                                </button>
                            </div>

                            <div className="movie-card-grid" style={{
                                display: 'grid',
                                gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
                                gap: '2rem'
                            }}>
                                {(() => {
                                    const filtered = historyItems.filter(item => historyFilter === 'all' || item.source === historyFilter);

                                    if (filtered.length === 0) return (
                                        <div style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '4rem', color: 'var(--text-muted)' }}>
                                            No history found for this category.
                                        </div>
                                    );

                                    return filtered.map((item, idx) => (
                                        <div key={`history-wrapper-${item.id}-${idx}`} style={{ position: 'relative' }} className="history-item-container">
                                            {item.source === 'music' ?
                                                <MusicCard movie={item} onClick={handleItemClick} /> :
                                                <MovieCard movie={item} onClick={handleItemClick} />
                                            }
                                            <button
                                                onClick={(e) => handleRemoveHistoryItem(e, item.id)}
                                                style={{
                                                    position: 'absolute',
                                                    top: '12px',
                                                    right: '12px',
                                                    width: '32px',
                                                    height: '32px',
                                                    borderRadius: '50%',
                                                    background: 'rgba(0,0,0,0.8)',
                                                    border: '1px solid rgba(255,255,255,0.4)',
                                                    color: '#fff',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    justifyContent: 'center',
                                                    cursor: 'pointer',
                                                    zIndex: 100,
                                                    transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
                                                    fontSize: '16px',
                                                    opacity: 0.7,
                                                    backdropFilter: 'blur(8px)',
                                                    pointerEvents: 'auto'
                                                }}
                                                className="remove-history-btn"
                                                title="Remove from history"
                                            >
                                                ✕
                                            </button>
                                        </div>
                                    ));
                                })()}
                            </div>
                        </div>
                    )}

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
                        {(Array.isArray(results) ? results : []).map((item) => (
                            item && item.id ? (
                                item.source === 'music' ?
                                    <MusicCard key={item.id} movie={item} onClick={handleItemClick} /> :
                                    <MovieCard key={item.id} movie={item} onClick={handleItemClick} />
                            ) : null
                        ))}
                    </div>

                    {results.length === 0 && !loading && activeSource !== 'history' && (
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
                            ) : homepageContent && homepageContent.length > 0 ? (
                                <div style={{ paddingBottom: '4rem' }}>
                                    {homepageContent.map((group, index) => (
                                        group._novelWelcome ? (
                                            /* Novel Welcome Screen */
                                            <div key={index} style={{ textAlign: 'center', padding: '4rem 2rem', maxWidth: '600px', margin: '0 auto' }}>
                                                <div style={{ fontSize: '4rem', marginBottom: '1.5rem' }}>📚</div>
                                                <h2 style={{ fontSize: '2rem', fontWeight: '700', marginBottom: '1rem', background: 'linear-gradient(135deg, var(--primary), #a855f7)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                                                    Novel Library
                                                </h2>
                                                <p style={{ fontSize: '1.1rem', color: 'var(--text-muted)', marginBottom: '0.75rem', lineHeight: '1.6' }}>
                                                    Search for any novel by name using our DuckDuckGo-powered search engine.
                                                </p>
                                                <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)', opacity: 0.7, lineHeight: '1.6' }}>
                                                    Supports RoyalRoad, ScribbleHub, NovelFull, and hundreds more sources.
                                                    Once you open a novel, you can read its chapters directly in the browser.
                                                </p>
                                                <div style={{ marginTop: '2rem', display: 'flex', gap: '1rem', justifyContent: 'center', flexWrap: 'wrap' }}>
                                                    {['Shadow Slave', 'Mother of Learning', 'Solo Leveling', 'Overlord'].map(s => (
                                                        <button key={s} onClick={() => handleSearch(s)}
                                                            style={{ padding: '0.5rem 1.2rem', borderRadius: '20px', border: '1px solid var(--border-glass)', background: 'rgba(255,255,255,0.05)', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '0.85rem', transition: 'all 0.2s' }}
                                                            onMouseEnter={e => { e.target.style.background = 'var(--primary)'; e.target.style.color = '#fff'; }}
                                                            onMouseLeave={e => { e.target.style.background = 'rgba(255,255,255,0.05)'; e.target.style.color = 'var(--text-muted)'; }}
                                                        >
                                                            {s}
                                                        </button>
                                                    ))}
                                                </div>
                                            </div>
                                        ) : (
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
                                                <div className={group.type === 'news' ? "news-grid" : "movie-card-grid"} style={{
                                                    display: 'grid',
                                                    gridTemplateColumns: group.type === 'news' ? 'repeat(auto-fill, minmax(300px, 1fr))' : 'repeat(auto-fill, minmax(220px, 1fr))',
                                                    gap: '2rem'
                                                }}>
                                                    {group.items.map((item, idx) => (
                                                        group.type === 'news' ?
                                                            <NewsCard key={item.id || idx} item={item} onClick={(it) => setNewsReaderItem(it)} API_BASE={CLOUD_BASE} /> :
                                                            (activeSource === 'music' ?
                                                                <MusicCard key={`${item.id}-${index}-${idx}`} movie={item} onClick={handleItemClick} /> :
                                                                <MovieCard key={`${item.id}-${index}-${idx}`} movie={item} onClick={handleItemClick} />)
                                                    ))}
                                                </div>
                                            </div>
                                        )
                                    ))}
                                </div>
                            ) : (
                                <div style={{ textAlign: 'center', color: 'var(--text-muted)', marginTop: '4rem', padding: '2rem', border: '1px dashed var(--border-glass)', borderRadius: 'var(--radius-md)' }}>
                                    {activeSource === 'cinecli' ? (
                                        <div>
                                            <h3>CineCLI Integration Ready</h3>
                                            <p>Search for torrents using the search bar above.</p>
                                        </div>
                                    ) : activeSource === 'anicli' ? (
                                        <div>
                                            <h3>Ani-CLI (Allmanga) Ready</h3>
                                            <p>Search for anime via the terminal-style scraper.</p>
                                        </div>
                                    ) : (
                                        <>
                                            <p style={{ fontSize: '1.2rem' }}>Start by searching for content.</p>
                                            <p style={{ fontSize: '0.9rem', marginTop: '1rem', opacity: 0.7 }}>
                                                Connected to: {API_BASE}
                                            </p>
                                        </>
                                    )}
                                </div>
                            )}
                        </>
                    )}
                </main>
            </div>

            {
                selectedItem && !novelReaderItem && !mangaReaderItem && (
                    <DetailsModal
                        item={selectedItem}
                        onClose={() => {
                            setSelectedItem(null);
                            setDetailsLoading(false); // Reset loading state
                            navigate('/');
                        }}
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
                        serverMode="local"
                        API_BASE={getTargetBase(selectedItem.source)}
                        detailsLoading={detailsLoading}
                    />
                )
            }

            {/* In-App Watch Page */}
            {videoPlayerData && (
                <WatchPage
                    key={`watch-${videoPlayerData.item.id}`}
                    item={videoPlayerData.item}
                    initialSeason={videoPlayerData.season}
                    initialEpisode={videoPlayerData.episode}
                    API_BASE={getTargetBase(videoPlayerData.item.source)}
                    onBack={() => {
                        const src = videoPlayerData.item && videoPlayerData.item.source ? videoPlayerData.item.source : 'moviebox';
                        const type = videoPlayerData.item && videoPlayerData.item.type ? videoPlayerData.item.type : 'movie';
                        navigate(`/details/${videoPlayerData.item.id}?source=${encodeURIComponent(src)}&type=${encodeURIComponent(type)}`);
                    }}
                    preloadedEpisodes={videoPlayerData.animeEpisodes}
                />
            )}

            {mangaReaderItem && (
                <MangaReader
                    key={`manga-${mangaReaderItem.item.id}`}
                    item={mangaReaderItem.item}
                    chapterId={mangaReaderItem.chapterId}
                    chapterTitle={mangaReaderItem.chapterTitle}
                    API_BASE={API_BASE}
                    onBack={() => setMangaReaderItem(null)}
                />
            )}

            {novelReaderItem && (
                <NovelReader
                    item={novelReaderItem.item}
                    chapterId={novelReaderItem.chapterId}
                    chapterTitle={novelReaderItem.chapterTitle}
                    API_BASE={API_BASE}
                    onBack={() => setNovelReaderItem(null)}
                    onChapterChange={(newId, newTitle) => {
                        setNovelReaderItem(prev => ({ ...prev, chapterId: newId, chapterTitle: newTitle }));
                    }}
                />
            )}

            {activeTrack && (
                <MusicPlayer
                    track={activeTrack}
                    onClose={() => setActiveTrack(null)}
                />
            )}

            {newsReaderItem && (
                <NewsReader
                    articleId={newsReaderItem.id}
                    onClose={() => setNewsReaderItem(null)}
                    API_BASE={CLOUD_BASE}
                />
            )}


            {/* Manual IP Modal */}
            {showManualIP && (
                <div className="modal-backdrop" onClick={() => setShowManualIP(false)}>
                    <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: '450px', flexDirection: 'column', padding: '1.5rem' }}>
                        <h3 style={{ marginTop: 0, marginBottom: '0.5rem' }}>MovieBox Settings</h3>
                        <p style={{ color: 'var(--text-muted)', marginBottom: '1.5rem', fontSize: '0.9rem' }}>
                            Enter your Local MovieBox Server URL or Tunnel address.
                        </p>

                        <div style={{ marginBottom: '1.5rem' }}>
                            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)' }}>SERVER URL</label>
                            <input
                                type="text"
                                className="input-glass"
                                placeholder="http://192.168.x.x:8080 or https://tunnel.com"
                                value={manualIPInput}
                                onChange={(e) => setManualIPInput(e.target.value)}
                                style={{ width: '100%', padding: '0.8rem 1.2rem' }}
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
                                        // Sanitize URL
                                        let url = manualIPInput.trim();

                                        // Auto-add protocol if missing
                                        if (!url.startsWith('http')) {
                                            // Default to https for tunnels/domains, http for IPs/localhost
                                            if (url.includes('.') && !url.match(/^\d+\./) && !url.includes('localhost')) {
                                                url = 'https://' + url;
                                            } else {
                                                url = 'http://' + url;
                                            }
                                        }

                                        if (url.endsWith('/')) url = url.slice(0, -1);

                                        // Cloud/Tunnel specific handling: do NOT append ports for these
                                        const isCloudUrl = url.includes('trycloudflare.com') ||
                                            url.includes('.github.dev') ||
                                            url.includes('.onrender.com') ||
                                            url.includes('.localtunnel.me') ||
                                            url.includes('.ngrok.io') ||
                                            url.includes('.vercel.app');

                                        const findBackendPort = async (baseUrl) => {
                                            // If it's a known cloud URL or already has a port, try it as is first
                                            if (isCloudUrl || baseUrl.match(/:\d+$/)) {
                                                try {
                                                    const res = await fetch(`${baseUrl}/api/health`, { timeout: 2000 });
                                                    if (res.ok) return baseUrl;
                                                } catch (e) { }
                                            }

                                            // Fallback logic for IPs or broken ports
                                            const baseWithoutPort = baseUrl.replace(/:\d+$/, '');
                                            const check = async (port) => {
                                                const controller = new AbortController();
                                                const id = setTimeout(() => controller.abort(), 1500);
                                                try {
                                                    const res = await fetch(`${baseWithoutPort}:${port}/api/health`, { signal: controller.signal });
                                                    clearTimeout(id);
                                                    if (res.ok) return `${baseWithoutPort}:${port}`;
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

                                            localStorage.setItem('moviebox_local_ip', targetUrl);
                                            setShowManualIP(false);

                                            // Test connection
                                            fetch(`${targetUrl}/api/health`)
                                                .then(res => {
                                                    if (res.ok) alert(`Successfully connected to ${targetUrl}`);
                                                    else alert(`Connected to ${targetUrl} but health check failed.`);
                                                })
                                                .catch(() => alert(`Connected to ${targetUrl} but unreachable.`));
                                        };

                                        // Decide strategy
                                        if (isCloudUrl) {
                                            // For cloud URLs, try as is (strip :8080 if accidentally entered or detected)
                                            let directUrl = url;
                                            if (directUrl.includes('github.dev') || directUrl.includes('render.com')) {
                                                directUrl = directUrl.replace(/:8080$/, '').replace(/:8000$/, '');
                                            }

                                            findBackendPort(directUrl).then(foundUrl => {
                                                setFoundUrl(foundUrl || directUrl);
                                            });
                                        } else {
                                            // For standard IPs, use the fallback scanner
                                            findBackendPort(url).then(foundUrl => {
                                                setFoundUrl(foundUrl || (url.includes(':') && (url.match(/:/g) || []).length >= 2 ? url : url + ':8080'));
                                            });
                                        }
                                    }
                                }}
                            >
                                Save & Connect
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export default App;
