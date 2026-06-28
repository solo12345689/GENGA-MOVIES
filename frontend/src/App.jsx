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
import TVDiscovery from './components/TVDiscovery';
import RadioDiscovery from './components/RadioDiscovery';
import RadioPlayer from './components/RadioPlayer';
import './styles/index.css';

// Define available backends
const CLOUD_BASE = 'https://genga-movies.onrender.com';
const NEWS_API_BASE = 'https://api-consumet-org-x46x.onrender.com';


function App() {
    // State for local server configuration

    const navigate = useNavigate();
    const location = useLocation();

    const [isSidebarOpen, setIsSidebarOpen] = useState(true);
    const internalNavRef = React.useRef(false);

    const [localServerURL, setLocalServerURL] = useState(() => {
        const saved = localStorage.getItem('moviebox_local_ip');
        return saved !== null ? saved : 'http://localhost:8000';
    });

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

    // Simplified connection logic
    useEffect(() => {
        const savedIP = localStorage.getItem('moviebox_local_ip');
        if (!savedIP) {
            localStorage.setItem('moviebox_local_ip', 'http://localhost:8000');
        }
    }, []);


    // Helper to determine target base URL for a given source
    const getTargetBase = (src = activeSource) => {
        if (src === 'home') return localServerURL;
        return (src === 'anilist' || src === 'manga' || src === 'music' || src === 'news' || src === 'tv' || src === 'radio')
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
    const [activeRadioStation, setActiveRadioStation] = useState(null);
    const [downloadProgress, setDownloadProgress] = useState(null);
    const [homepageContent, setHomepageContent] = useState(null);
    const [homepageLoading, setHomepageLoading] = useState(false);
    const [globalError, setGlobalError] = useState(null);

    useEffect(() => {
        const handleError = (event) => {
            setGlobalError(event.error?.message || event.message || "Unknown Error");
            console.error("Global Error:", event);
        };
        window.addEventListener('error', handleError);
        window.addEventListener('unhandledrejection', (e) => {
            setGlobalError(e.reason?.message || "Promise Rejection");
        });
        return () => {
            window.removeEventListener('error', handleError);
        };
    }, []);

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
                let endpoint = '/api/homepage';
                if (activeSource === 'anilist') endpoint = '/api/anime/home';
                if (activeSource === 'manga') endpoint = '/api/manga/mangapill/popular';
                if (activeSource === 'music') endpoint = '/api/music/home';
                if (activeSource === 'news') {
                    const newsRes = await fetch(`${NEWS_API_BASE}/news/ann/recent-feeds`);
                    if (newsRes.ok) {
                        const newsData = await newsRes.json();
                        setHomepageContent([{ title: 'Latest Anime & Manga News', items: newsData, type: 'news' }]);
                        setHomepageLoading(false);
                        return;
                    }
                }

                const res = await fetch(`${API_BASE}${endpoint}`);
                if (res.ok) {
                    const data = await res.json();
                    
                    // Detect backend block
                    const isBlocked = activeSource === 'anilist' && Array.isArray(data) && data.length === 1 && data[0].id === 'error';
                    if (isBlocked) throw new Error("Backend IP Blocked");

                    if (activeSource === 'moviebox' || activeSource === 'home') {
                        setHomepageContent(data.groups.map(g => ({
                            ...g,
                            items: g.items.map(it => ({ ...it, source: 'moviebox' }))
                        })));
                    } else if (activeSource === 'anilist') {
                        setHomepageContent(data);
                    } else if (activeSource === 'manga') {
                        const results = data.results || [];
                        setHomepageContent([{
                            title: 'Popular Manga',
                            items: results.map(it => ({
                                ...it,
                                source: 'manga',
                                poster_url: `${API_BASE}/api/manga/image-proxy?url=${encodeURIComponent(it.poster_url)}`
                            }))
                        }]);
                    } else if (activeSource === 'tv') {
                        setHomepageContent([{ title: 'Live TV', items: [], _tvWelcome: true }]);
                        setHomepageLoading(false);
                        return;
                    } else if (activeSource === 'music' && data.groups) {
                        setHomepageContent(data.groups);
                    }
                } else {
                    throw new Error(`HTTP ${res.status}`);
                }
            } catch (err) {
                console.warn("[App] Backend failed, trying client-side fallback for Anilist:", err);
                if (activeSource === 'anilist') {
                    try {
                        const query = `query { Page(page: 1, perPage: 20) { media(type: ANIME, sort: TRENDING_DESC, status_not: NOT_YET_RELEASED) { id title { romaji english native } coverImage { extraLarge large } bannerImage episodes description status nextAiringEpisode { episode } } } }`;
                        const aRes = await fetch('https://graphql.anilist.co', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ query })
                        });
                        if (aRes.ok) {
                            const { data } = await aRes.json();
                            const results = (data?.Page?.media || []).map(m => ({
                                id: String(m.id),
                                title: m.title.english || m.title.romaji || m.title.native,
                                poster_url: m.coverImage.extraLarge || m.coverImage.large,
                                banner_url: m.bannerImage,
                                description: m.description,
                                episodes: m.episodes,
                                type: 'anime',
                                source: 'anilist'
                            }));
                            setHomepageContent([{ title: "Trending Now (Direct)", items: results }]);
                            return;
                        }
                    } catch (ae) { console.error(ae); }
                }
                setHomepageContent([]);
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
        let ws;
        let reconnectTimeout;
        let didUnmount = false;

        const connect = () => {
            if (didUnmount) return;
            const wsUrl = API_BASE
                ? API_BASE.replace(/^http/, 'ws') + '/api/ws'
                : (window.location.protocol === 'https:' ? 'wss://' : 'ws://') + window.location.host + '/api/ws';

            try {
                ws = new WebSocket(wsUrl);

                ws.onopen = () => {
                    // Silent connection
                };

                ws.onmessage = (event) => {
                    try {
                        const data = JSON.parse(event.data);
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
                        // Silent error
                    }
                };

                ws.onclose = () => {
                    if (!didUnmount) {
                        // Use a longer backoff (30s) for non-local URLs to reduce console spam on cloud backends
                        const isCloud = API_BASE && (API_BASE.includes('render.com') || API_BASE.includes('ngrok') || API_BASE.includes('loca.lt'));
                        const delay = isCloud ? 30000 : 5000;
                        reconnectTimeout = setTimeout(connect, delay);
                    }
                };

                ws.onerror = () => {
                    if (ws) ws.close();
                };
            } catch (err) {
                if (!didUnmount) {
                    const isCloud = API_BASE && (API_BASE.includes('render.com') || API_BASE.includes('ngrok'));
                    const delay = isCloud ? 30000 : 5000;
                    reconnectTimeout = setTimeout(connect, delay);
                }
            }
        };

        connect();

        return () => {
            didUnmount = true;
            if (ws) {
                ws.onclose = null;
                ws.onerror = null;
                ws.onopen = null;
                // Only close if it's OPEN
                if (ws.readyState === WebSocket.OPEN) {
                    ws.close();
                } else if (ws.readyState === WebSocket.CONNECTING) {
                    // Nulled handlers ensure it dies quietly when it finishes opening
                }
            }
            if (reconnectTimeout) clearTimeout(reconnectTimeout);
        };
    }, [API_BASE]); // Re-connect when API_BASE changes

    const handleSearch = async (query, type = 'all') => {
        // TV section has its own built-in filter — don't run global search
        if (activeSource === 'tv') return;

        setLoading(true);
        try {
            let endpoint = `/api/search?query=${encodeURIComponent(query)}&content_type=${type}`;
            const base = getTargetBase(activeSource);

            if (activeSource === 'anilist') {
                endpoint = `/api/anime/search?query=${encodeURIComponent(query)}`;
            } else if (activeSource === 'cinecli') {
                endpoint = `/api/cinecli/search?query=${encodeURIComponent(query)}`;
            } else if (activeSource === 'manga') {
                endpoint = `/api/manga/search?query=${encodeURIComponent(query)}`;
            } else if (activeSource === 'music') { 
                endpoint = `/api/music/search?query=${encodeURIComponent(query)}`;
            }

            const res = await fetch(`${base}${endpoint}`);
            
            // Detect backend block for search
            if (activeSource === 'anilist') {
                const data = await res.json();
                const isBlocked = Array.isArray(data) && data.length === 1 && data[0].id === 'error';
                if (isBlocked) throw new Error("Search Backend Blocked");
                setResults(data);
                return;
            }

            const data = await res.json();

            if (activeSource === 'manga') {
                setResults((data.results || []).map(it => ({
                    ...it,
                    source: 'manga',
                    poster_url: `${base}/api/manga/image-proxy?url=${encodeURIComponent(it.poster_url)}`
                })));
            } else if (activeSource === 'music') {
                setResults((data.results || []).map(it => ({ ...it, source: 'music' })));
            } else {
                setResults((data.results || []).map(it => {
                    let determinedType = it.type;
                    if (typeof it.type !== 'string') {
                        determinedType = it.type === 2 ? 'series' : 'movie';
                    }
                    return { ...it, source: 'moviebox', type: determinedType };
                }));
            }
        } catch (err) {
            console.warn("[App] Search backend failed, trying client-side fallback for Anilist:", err);
            
            if (activeSource === 'anilist') {
                try {
                    const queryGQL = `query { Page(page: 1, perPage: 20) { media(type: ANIME, search: "${query.replace(/"/g, '\\"')}", status_not: NOT_YET_RELEASED) { id title { romaji english native } coverImage { extraLarge large } bannerImage episodes description status } } }`;
                    const aRes = await fetch('https://graphql.anilist.co', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ query: queryGQL })
                    });
                    if (aRes.ok) {
                        const { data } = await aRes.json();
                        const results = (data?.Page?.media || []).map(m => ({
                            id: String(m.id),
                            title: m.title.english || m.title.romaji || m.title.native,
                            poster_url: m.coverImage.extraLarge || m.coverImage.large,
                            banner_url: m.bannerImage,
                            description: m.description,
                            episodes: m.episodes,
                            type: 'anime',
                            source: 'anilist'
                        }));
                        setResults(results);
                        return;
                    }
                } catch (ae) { console.error(ae); }
            }
            
            const isColdStart = err.message === 'Failed to fetch' || err.message.includes('timeout');
            const coldStartMsg = isColdStart ? "\n\nNote: This might be a 'Cold Start'. Please wait 30 seconds and try again." : "";
            alert(`Search Failed!\n\nError: ${err.message}${coldStartMsg}`);
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
            if (s === 'anilist') return it.animeEpisodes && it.animeEpisodes.length > 0;
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

    // Use a ref to prevent double-execution of streams (e.g. StrictMode or ghost clicks)
    const streamGuardRef = React.useRef(null);
    const handleStream = async (item, season = null, episode = null) => {
        if (!item) return;

        // Simple debounce guard
        const now = Date.now();
        if (streamGuardRef.current && streamGuardRef.current.id === item.id && (now - streamGuardRef.current.time < 500)) {
            return;
        }
        streamGuardRef.current = { id: item.id, time: now };

        if (item.source === 'music' || item.type === 'music' || item.type === 'music_playlist') {
            handleMusicPlay(item);
            return;
        }

        if (item.type === 'manga') {
            setMangaReaderItem({ item, chapterId: item.chapterId, chapterTitle: item.chapterTitle });
            return;
        }

        if (item.type === 'novel') {
            setNovelReaderItem({ item, chapterId: item.chapterId, chapterTitle: item.chapterTitle });
            return;
        }

        // console.log("[App] handleStream called for:", item && item.title);

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
            episode: episode || null,
            animeEpisodes: item && item.animeEpisodes ? item.animeEpisodes : null
        };
        // Navigate to watch route with episode and source params
        const params = new URLSearchParams();
        if (episode !== null && episode !== undefined) params.set('episode', String(episode));
        if (season !== null && season !== undefined) params.set('season', String(season));
        params.set('source', src);

        // For TV channels, pass the stream URL and type in the query so loadWatch can reconstruct state
        if (src === 'tv') {
            if (item.url) params.set('url', item.url);
            if (item.stream_type) params.set('stream_type', item.stream_type);
            if (item.title) params.set('title', item.title);
            if (item.yt_id) params.set('yt_id', item.yt_id);
        }

        internalNavRef.current = true;
        setVideoPlayerData(preload);

        const watchUrl = `/watch/${encodeURIComponent(item.id)}?${params.toString()}`;
        // console.log("[App] handleStream navigating to:", watchUrl);
        navigate(watchUrl);

        // ALWAYS close modal manually upon streaming to avoid UI overlap
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

    useEffect(() => {
        try {
            // Keep UI in sync with React Router location
        const pathname = location.pathname || '/';
        const search = location.search || '';

        const loadDetails = async (id, source, type = 'movie') => {
            // TV channels don't have a details page — just clear state
            if (source === 'tv') {
                setDetailsLoading(false);
                return;
            }
            // If loadDetails is called, it means we definitely need to fetch more data.
            // We set detailsLoading(true) to show the prominent spinner.
            setDetailsLoading(true);

            console.log(`[App] loadDetails starting for ID: ${id}, Source: ${source}`);
            // Determine appropriate base URL for this source
            const base = getTargetBase(source);
            console.log(`[App] Using base URL for fetch: ${base}`);

            try {
                if (source === 'cinecli') {
                    const res = await fetch(`${base}/api/cinecli/details/${id}`);
                    const details = await res.json();
                    setSelectedItem(prev => ({ ...(prev || {}), ...details, source: 'cinecli', hasFullDetails: true }));
                } else if (source === 'anilist') {
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
                        ...(prev || {}),
                        ...(details.id ? details : { id, title: details.title || (prev && prev.title) || '' }),
                        animeEpisodes: episodes,
                        type: 'anime',
                        source: 'anilist',
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
                } else if (source === 'music') {
                    const res = await fetch(`${base}/api/music/info?seokey=${id}&type=${type}`);
                    const details = await res.json();
                    setSelectedItem(prev => ({
                        ...(prev || {}),
                        ...details,
                        source: 'music',
                        type: type || 'music',
                        hasFullDetails: true
                    }));
                } else {
                    const res = await fetch(`${base}/api/details/${id}?type=${type}`);
                    const details = await res.json();
                    setSelectedItem(prev => ({ ...(prev || {}), ...details, source: 'moviebox', hasFullDetails: true }));
                }
            } catch (e) {
                console.error('Failed to load details for route', e);
            } finally {
                setDetailsLoading(false);
            }
        };

        const loadWatch = async (id, ep, source = 'moviebox', season = null) => {
            console.log("[App] loadWatch triggered for:", id, "Source:", source);
            try {
                let details = { id, source }; // Default with known info
                if (source === 'anilist') {
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
                    const item = { ...details, id, source: 'anilist', type: 'anime', hasFullDetails: true };
                    setVideoPlayerData({ item, season: season || null, episode: ep || null, animeEpisodes: episodes });
                    setSelectedItem(null);
                    return;
                }

                // TV channels: no details endpoint, just play directly
                if (source === 'tv') {
                    const params = new URLSearchParams(location.search);
                    const url = params.get('url');
                    const ytId = params.get('yt_id');
                    const streamType = params.get('stream_type') || 'hls';
                    // Decode title — it was encoded with encodeURIComponent
                    const rawTitle = params.get('title') || '';
                    const title = rawTitle || id;
                    // console.log("[App] loadWatch TV data reconstructed:", { id, url, title, ytId });
                    setVideoPlayerData({ 
                        item: { id, source: 'tv', type: 'channel', url, stream_type: streamType, title, yt_id: ytId }, 
                        season: null, 
                        episode: null 
                    });
                    setSelectedItem(null);
                    return;
                }

                // Default MovieBox flow
                const base = getTargetBase(source);
                const res = await fetch(`${base}/api/details/${id}`);
                if (res.ok) {
                    const d = await res.json();
                    const item = { ...d, id, source, type: (d.type || 'movie'), hasFullDetails: true };
                    setVideoPlayerData({ item, season: season || null, episode: ep || null });
                    setSelectedItem(null);
                } else {
                    setVideoPlayerData({ item: { id, source, type: 'movie' }, season: season || null, episode: ep || null });
                }
            } catch (e) {
                setVideoPlayerData({ item: { id, source, type: 'movie' }, season: season || null, episode: ep || null });
            }
        };

        // Route handling
        // console.log("[App] Route Sync Hook triggered. Path:", pathname, "Params:", search);

        // Group route handlers to avoid clearing state during transitions
        if (pathname.startsWith('/details/')) {
            // Guard: If we are navigating TOWARDS a player/reader, don't clear state or reload details.
            if (internalNavRef.current) {
                internalNavRef.current = false; // Reset now that we are at the route 
                return;
            }

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
                setSelectedItem(null); // Ensure modal is closed when watching/reading
                effectiveItem = videoPlayerData.item;
            } else if (mangaReaderItem && String(mangaReaderItem.item.id) === String(id)) {
                setSelectedItem(mangaReaderItem.item);
                effectiveItem = mangaReaderItem.item;
            }

            // Ensure other main views are cleared when viewing details
            setVideoPlayerData(null);
            setMangaReaderItem(null);
            setNewsReaderItem(null);

            // Determine if the item is "full enough" for the requested ID
            const isFullItem = (it) => {
                if (!it || String(it.id) !== String(id)) return false;
                if (!it.hasFullDetails) return false;

                // Source-specific checks
                if (source === 'anilist') return it.animeEpisodes && it.animeEpisodes.length > 0;
                if (source === 'manga') return it.volumes && Object.keys(it.volumes || {}).length > 0;
                if (source === 'music') return (it.tracks?.length > 0) || (it.songs?.length > 0);
                if (it.type === 'series' || it.type === 'anime') return it.seasons && it.seasons.length > 0;

                return !!(it.plot || it.description);
            };

            if (!isFullItem(effectiveItem)) {
                loadDetails(id, source, type);
            }
            return;
        }

        if (pathname.startsWith('/watch/')) {
            internalNavRef.current = false; // Destination reached
            const id = pathname.replace('/watch/', '').split('/')[0];
            const params = new URLSearchParams(search);
            const ep = params.get('episode');
            const season = params.get('season');
            const source = params.get('source') || 'moviebox';

            if (source !== activeSource && source !== 'home' && activeSource !== 'history') {
                setActiveSource(source);
            }

            const shouldReload = !videoPlayerData ||
                String(videoPlayerData.item.id) !== String(id) ||
                (source !== 'tv' && String(videoPlayerData.episode) !== String(ep));

            setSelectedItem(null);
            if (shouldReload) {
                loadWatch(id, ep, source, season);
            }
            return;
        }

        // Fallback for Home/Root
        if (pathname === '/' || pathname === '' || pathname === '/home') {
            if (internalNavRef.current) {
                internalNavRef.current = false;
                return;
            }
            setSelectedItem(null);
            setVideoPlayerData(null);
            setMangaReaderItem(null);
            setNewsReaderItem(null);
            return;
        }

        // Reset guard if we are on any other route
        internalNavRef.current = false;
        } catch (err) {
            console.error("[App] Routing effect crashed:", err);
        }
    }, [location, API_BASE]);

    return (
        <div className="app" style={{ display: 'flex', flexDirection: 'row', maxWidth: '100vw', overflow: 'hidden' }}>

            {/* NEW SIDEBAR */}
            {!videoPlayerData && !mangaReaderItem && (
                <Sidebar
                    activeSource={activeSource}
                    onChangeSource={setActiveSource}
                    serverStatus={serverStatus}
                    isOpen={isSidebarOpen}
                    onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
                />
            )}

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
                                activeSource === 'anilist' ? 'Anime World' :
                                    activeSource === 'manga' ? 'Manga Collection' :
                                        activeSource === 'music' ? 'Music Library' :
                                            activeSource === 'news' ? 'News Feed' :
                                                activeSource === 'tv' ? 'Live TV' :
                                                    activeSource === 'radio' ? 'Radio Stations' :
                                                        activeSource === 'history' ? 'Watch History' : 'Genga Movies'}

                    </div>

                    {/* Top Bar with Search */}
                    {activeSource !== 'history' && activeSource !== 'news' && activeSource !== 'tv' && activeSource !== 'radio' && (
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
                                            activeSource === 'anilist' ? "Search anime..." :
                                                'Search for movies or series...'}

                            />
                        </div>
                    )}

                    {activeSource === 'history' && (
                        <div style={{ padding: '1rem 0' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                                <div style={{ display: 'flex', gap: '0.5rem' }}>
                                    {['all', 'moviebox', 'anilist', 'manga', 'music'].map(f => (
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
                                            {f === 'anilist' ? 'Anime' : f === 'moviebox' ? 'Home' : f}
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

                    {activeSource === 'tv' && results.length === 0 && (
                        <TVDiscovery API_BASE={API_BASE} onStream={handleStream} />
                    )}

                    {activeSource === 'radio' && results.length === 0 && (
                        <RadioDiscovery API_BASE={API_BASE} onStream={(station) => setActiveRadioStation(station)} />
                    )}

                    {results.length === 0 && !loading && activeSource !== 'history' && activeSource !== 'tv' && activeSource !== 'radio' && (
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
                                        group._tvWelcome ? (
                                            <TVDiscovery key={index} API_BASE={API_BASE} onStream={handleStream} />
                                        ) : group._radioWelcome ? (
                                            <RadioDiscovery key={index} API_BASE={API_BASE} onStream={(station) => setActiveRadioStation(station)} />
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
                                                            <NewsCard key={item.id || idx} item={item} onClick={(it) => setNewsReaderItem(it)} API_BASE={NEWS_API_BASE} /> :
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
                selectedItem && !mangaReaderItem && (
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
                        const item = videoPlayerData.item;
                        const src = item && item.source ? item.source : 'moviebox';
                        // TV channels should go back to the TV section, not open DetailsModal
                        if (src === 'tv') {
                            setVideoPlayerData(null);
                            navigate('/');
                        } else {
                            const type = item && item.type ? item.type : 'movie';
                            internalNavRef.current = true; // GUARD TRANSITION
                            setSelectedItem(item); // INSTANT RECOVERY
                            setVideoPlayerData(null); // INSTANT HIDE PLAYER
                            navigate(`/details/${item.id}?source=${encodeURIComponent(src)}&type=${encodeURIComponent(type)}`);
                        }
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
                    onBack={() => {
                        const item = mangaReaderItem.item;
                        const type = item && item.type ? item.type : 'manga';
                        const src = item && item.source ? item.source : 'manga';
                        internalNavRef.current = true; // GUARD TRANSITION
                        setSelectedItem(item); // INSTANT RECOVERY
                        setMangaReaderItem(null); // INSTANT HIDE READER
                        navigate(`/details/${item.id}?source=${encodeURIComponent(src)}&type=${encodeURIComponent(type)}`);
                    }}
                />
            )}


            {activeTrack && (
                <MusicPlayer
                    track={activeTrack}
                    onClose={() => setActiveTrack(null)}
                />
            )}

            {activeRadioStation && (
                <RadioPlayer
                    station={activeRadioStation}
                    onClose={() => setActiveRadioStation(null)}
                />
            )}

            {newsReaderItem && (
                <NewsReader
                    articleId={newsReaderItem.id}
                    onClose={() => setNewsReaderItem(null)}
                    API_BASE={NEWS_API_BASE}
                />
            )}


            {/* Manual IP Modal */}
            {showManualIP && (
                <div className="modal-backdrop" onClick={() => setShowManualIP(false)}>
                    <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: '450px', flexDirection: 'column', padding: '1.5rem' }}>
                        <h3 style={{ marginTop: 0, marginBottom: '0.5rem' }}>Genga Settings</h3>
                        <p style={{ color: 'var(--text-muted)', marginBottom: '1.5rem', fontSize: '0.9rem' }}>
                            Enter your local server URL or Tunnel address.
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

                                            const port8000 = await check(8000);
                                            if (port8000) return port8000;

                                            const port8080 = await check(8080);
                                            if (port8080) return port8080;

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
                                                setFoundUrl(foundUrl || (url.includes(':') && (url.match(/:/g) || []).length >= 2 ? url : url + ':8000'));
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
            {globalError && (
                <div style={{
                    position: 'fixed',
                    bottom: '20px',
                    left: '50%',
                    transform: 'translateX(-50%)',
                    background: '#ef4444',
                    color: 'white',
                    padding: '10px 20px',
                    borderRadius: '8px',
                    zIndex: 9999,
                    fontSize: '0.85rem',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px'
                }}>
                    <span>⚠️ Error: {globalError}</span>
                    <button onClick={() => setGlobalError(null)} style={{ background: 'rgba(255,255,255,0.2)', border: 'none', color: 'white', cursor: 'pointer', borderRadius: '4px', padding: '2px 6px' }}>Dismiss</button>
                    <button onClick={() => window.location.reload()} style={{ background: 'white', border: 'none', color: '#ef4444', cursor: 'pointer', borderRadius: '4px', padding: '2px 8px', fontWeight: 'bold' }}>Reload App</button>
                </div>
            )}
        </div>
    );
}

export default App;
