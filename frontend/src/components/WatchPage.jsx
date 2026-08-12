import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import VideoPlayer from './VideoPlayer';

const WatchPage = ({ item, initialSeason, initialEpisode, API_BASE, onBack, preloadedEpisodes }) => {
    // State
    const isTVChannel = item.source === 'tv' || item.type === 'channel';
    const isMovieContent = item.type === 'movie' || item.type === 'anime_movie';
    const [currentSeason, setCurrentSeason] = useState(initialSeason != null ? Number(initialSeason) : (isMovieContent ? null : 1));
    const [currentEpisode, setCurrentEpisode] = useState(initialEpisode != null ? Number(initialEpisode) : (isMovieContent ? null : 1));
    const [streamUrl, setStreamUrl] = useState(null);
    const [streamType, setStreamType] = useState('hls');
    const [subtitles, setSubtitles] = useState([]);
    const [loadingStream, setLoadingStream] = useState(false);
    const [seasonsData, setSeasonsData] = useState(item.seasons || []); // For MovieBox
    const [animeEpisodes, setAnimeEpisodes] = useState([]); // For Anilist
    const [tvPlaylistChannels, setTvPlaylistChannels] = useState([]);
    const [activeTvChannel, setActiveTvChannel] = useState(item);
    const [tvSearchQuery, setTvSearchQuery] = useState('');
    const [streamError, setStreamError] = useState(null);
    const formatStreamUrl = (rawUrl, sType) => {
        if (!rawUrl) return '';
        if (sType === 'embed' || rawUrl.includes('youtube.com') || rawUrl.includes('youtu.be')) return rawUrl;
        const isInternal = API_BASE ? rawUrl.includes(API_BASE) : rawUrl.includes(window.location.origin);
        if (!isInternal && (rawUrl.startsWith('http://') || rawUrl.startsWith('https://'))) {
            return `${API_BASE}/api/proxy-stream?url=${encodeURIComponent(rawUrl)}&source=tv`;
        }
        return rawUrl;
    };
    const [fullDetails, setFullDetails] = useState(item);
    const [loadingDetails, setLoadingDetails] = useState(false);
    const [activeSource] = useState(item.source || 'moviebox');
    const [animeLanguage, setAnimeLanguage] = useState(item.language || 'sub');
    // Manual Megaplay ID Override
    const [showManualInput, setShowManualInput] = useState(false);
    const [manualId, setManualId] = useState('');
    // Retry counter to re-trigger stream fetch without full page reload
    const [retryCounter, setRetryCounter] = useState(0);
    const lastFetchedRef = useRef({ id: '', season: null, episode: null, episodeId: '', source: '', retryCounter: 0, animeLanguage: '' });

    // Mobile Responsiveness
    // Detect Smart TV user agents to avoid mobile-stacked layout on TV devices
    const isSmartTV = (() => {
        try {
            const ua = navigator.userAgent || '';
            // Add common Smart TV / set-top / Jio browser identifiers
            return /SMART-TV|SmartTV|GoogleTV|Android TV|AndroidTV|AppleTV|Apple TV|NetCast|BRAVIA|AFT|HbbTV|SMARTTV|Set-Top|SetTop|STB|JioBrowser|Jio|JioTV/i.test(ua);
        } catch (e) {
            return false;
        }
    })();

    const [isMobile, setIsMobile] = useState(!isSmartTV && window.innerWidth <= 1024);
    const [showEpisodes, setShowEpisodes] = useState(true);
    const [useVideoJS, setUseVideoJS] = useState(false);

    useEffect(() => {
        const handleResize = () => setIsMobile(!isSmartTV && window.innerWidth <= 1024);
        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, [isSmartTV]);

    const navigate = useNavigate();
    const location = useLocation();

    // Sync current season/episode with URL search params
    useEffect(() => {
        // CRITICAL: Only sync URL if we are actually on the watch route.
        // If we are on /details/ it means the transition hasn't finished yet or we are going back.
        if (!location.pathname.startsWith('/watch/')) return;

        try {
            // Build new search params
            const params = new URLSearchParams(location.search || '');
            if (currentEpisode != null) params.set('episode', String(currentEpisode));
            else params.delete('episode');

            if (currentSeason != null) params.set('season', String(currentSeason));
            else params.delete('season');

            const search = params.toString();
            const currentSearch = location.search.replace('?', '');

            // Only navigate if search params actually changed to avoid loop/redirect
            if (search !== currentSearch) {
                // Replace the current history entry so navigation doesn't spam back-stack
                navigate(`${location.pathname}${search ? `?${search}` : ''}`, { replace: true });
            }
        } catch (e) {
            // ignore navigation errors
            console.error('Failed to sync episode to URL', e);
        }
        // Only run when episode/season change
    }, [currentEpisode, currentSeason, location.pathname, location.search, navigate]);

    // Respond to prop changes (when App navigates to a different /watch link)
    useEffect(() => {
        if (initialSeason != null && Number(initialSeason) !== currentSeason) {
            setCurrentSeason(Number(initialSeason));
        }
        if (initialEpisode != null && Number(initialEpisode) !== currentEpisode) {
            setCurrentEpisode(Number(initialEpisode));
        }
    }, [initialSeason, initialEpisode]);

    const getMaxEpisodes = () => {
        if (activeSource === 'moviebox') {
            if (!seasonsData.length) return 24;
            const seasonObj = seasonsData.find(s => s.season_number === currentSeason);
            return seasonObj ? seasonObj.max_episodes : 24;
        } else {
            return animeEpisodes.length;
        }
    };

    const getNextEpisode = () => {
        if (isMovieContent) return null;
        if (activeSource === 'moviebox') {
            const maxEp = getMaxEpisodes();
            if (currentEpisode < maxEp) return { season: currentSeason, episode: currentEpisode + 1 };
            const nextS = currentSeason + 1;
            if (seasonsData.some(s => s.season_number === nextS)) return { season: nextS, episode: 1 };
        } else {
            const idx = animeEpisodes.findIndex(e => e.number === currentEpisode);
            if (idx !== -1 && idx < animeEpisodes.length - 1) {
                const n = animeEpisodes[idx + 1];
                return { episodeId: n.episodeId, episodeNo: n.number };
            }
        }
        return null;
    };

    const hasNext = !!getNextEpisode();

    const handleNextEpisode = useCallback(() => {
        const next = getNextEpisode();
        if (next) {
            if (activeSource === 'moviebox') {
                setCurrentSeason(next.season);
                setCurrentEpisode(next.episode);
            } else {
                // Anilist logic
                setFullDetails(prev => ({ ...prev, episodeId: next.episodeId }));
                setCurrentEpisode(next.episodeNo);
            }
        }
    }, [activeSource, currentEpisode, currentSeason, animeEpisodes, seasonsData]);

    const handleManualLoad = () => {
        if (!manualId) return;
        // Use the native embed link with the manually entered ID
        const megaplayUrl = `https://megaplay.buzz/stream/s-2/${manualId}/${animeLanguage}`;
        const proxyUrl = `${API_BASE}/api/iframe-proxy?url=${encodeURIComponent(megaplayUrl)}`;

        console.log("[WatchPage] Manual Override (Proxy):", megaplayUrl);
        setStreamUrl(proxyUrl);
        setStreamType('embed');
        setStreamError(null);
        setLoadingStream(false);
        // We don't close the input so user can adjust if wrong
    };


    // Fetch Details & Episodes
    useEffect(() => {
        const fetchDetails = async () => {
            if (isMovieContent) return; // Covers TV channels too (isMovieContent=true for TV)
            if (isTVChannel) return;   // Extra guard
            setLoadingDetails(true);
            try {
                if (activeSource === 'moviebox') {
                    const res = await fetch(`${API_BASE}/api/details/${item.id}`);
                    const data = await res.json();
                    setFullDetails({ ...item, ...data });
                    // Ensure subtitle URLs are absolute to the backend API
                    const subs = (data.subtitles || []).map(s => ({
                        ...s,
                        url: s.url.startsWith('http') ? s.url : `${API_BASE}${s.url.startsWith('/') ? '' : '/'}${s.url}`
                    }));
                    setSubtitles(subs);
                    if (data.seasons) {
                        setSeasonsData(data.seasons);
                    }
                } else {
                    // Use preloaded episodes if provided (from App route loader)
                    if (preloadedEpisodes && preloadedEpisodes.length > 0) {
                        setAnimeEpisodes(preloadedEpisodes);
                    } else {
                        const res = await fetch(`${API_BASE}/api/anime/episodes/${item.id}`);
                        const data = await res.json();
                        if (data.status === 200 && data.data && data.data.episodes) {
                            setAnimeEpisodes(data.data.episodes);
                        }
                    }
                }
            } catch (err) {
                console.error("Failed to fetch details", err);
            } finally {
                setLoadingDetails(false);
            }
        };
        fetchDetails();
    }, [item.id, activeSource, API_BASE]);

    // Sync Episode ID when Episodes Load (Fix for Initial Load)
    useEffect(() => {
        if (activeSource === 'anilist' && animeEpisodes.length > 0 && !fullDetails.episodeId) {
            const ep = animeEpisodes.find(e => e.number === currentEpisode);
            if (ep) {
                console.log("[WatchPage] Syncing Episode ID for Auto-Play:", ep.episodeId);
                setFullDetails(prev => ({ ...prev, episodeId: ep.episodeId }));
                // This state update will trigger the stream fetching effect below
            }
        }
    }, [animeEpisodes, currentEpisode, activeSource, fullDetails.episodeId]); // Added fullDetails.episodeId to dependencies to prevent infinite loop if it's already set

    // Fetch Stream URL
    useEffect(() => {
        const isMB = activeSource === 'moviebox';
        const isAni = activeSource === 'anilist';
        if (isAni && !fullDetails.episodeId) {
            return;
        }

        const hasChanged = 
            lastFetchedRef.current.source !== activeSource ||
            lastFetchedRef.current.retryCounter !== retryCounter ||
            lastFetchedRef.current.animeLanguage !== animeLanguage ||
            (isMB && (
                lastFetchedRef.current.id !== item.id ||
                lastFetchedRef.current.season !== currentSeason ||
                lastFetchedRef.current.episode !== currentEpisode
            )) ||
            (isAni && (
                lastFetchedRef.current.episodeId !== fullDetails.episodeId
            )) ||
            (!isMB && !isAni && lastFetchedRef.current.id !== item.id);

        if (!hasChanged) {
            return;
        }

        lastFetchedRef.current = {
            id: item.id,
            season: currentSeason,
            episode: currentEpisode,
            episodeId: fullDetails.episodeId || '',
            source: activeSource,
            retryCounter,
            animeLanguage
        };

        const abortController = new AbortController();
        const timeoutId = setTimeout(() => abortController.abort(), 20000); // 20s timeout

        const fetchStream = async (retryCount = 0) => {
            try {
                setLoadingStream(true);
                setStreamError(null);

                if (activeSource !== 'moviebox') {
                    setSubtitles([]);
                }

                // --- TV CHANNELS ---
                if (activeSource === 'tv') {
                    if (item.stream_type === 'youtube_hls' && item.yt_id) {
                        const resolveUrl = `${API_BASE}/api/tv/resolve-youtube/${item.yt_id}`;
                        const res = await fetch(resolveUrl, { signal: abortController.signal });
                        const data = await res.json();
                        if (data.url) {
                            setStreamUrl(data.url);
                            setStreamType('hls');
                            setLoadingStream(false);
                            return;
                        } else {
                            console.warn("YouTube HLS resolution failed, falling back to Embed:", data.error);
                            const embedUrl = `https://www.youtube.com/embed/${item.yt_id}`;
                            setStreamUrl(embedUrl);
                            setStreamType('embed');
                            setLoadingStream(false);
                            return;
                        }
                    }

                    const targetUrl = (activeTvChannel && activeTvChannel.url) ? activeTvChannel.url : item.url;
                    if (!targetUrl) throw new Error('No stream URL available');

                    const isM3U = item.stream_type === 'm3u_playlist' || targetUrl.toLowerCase().endsWith('.m3u') || (targetUrl.toLowerCase().includes('.m3u') && !targetUrl.toLowerCase().includes('.m3u8'));



                    if (isM3U && tvPlaylistChannels.length === 0) {
                        try {
                            const cacheKey = `m3u_cache_${targetUrl}`;
                            const cached = sessionStorage.getItem(cacheKey);
                            let parsedChannels = [];
                            if (cached) {
                                try { parsedChannels = JSON.parse(cached); } catch (e) {}
                            }

                            if (!parsedChannels || parsedChannels.length === 0) {
                                const parseUrl = `${API_BASE}/api/tv/parse-playlist?url=${encodeURIComponent(targetUrl)}`;
                                const res = await fetch(parseUrl, { signal: abortController.signal });
                                const data = await res.json();
                                parsedChannels = data.results || [];
                                if (parsedChannels.length > 0) {
                                    sessionStorage.setItem(cacheKey, JSON.stringify(parsedChannels));
                                }
                            }

                            if (parsedChannels.length > 0) {
                                setTvPlaylistChannels(parsedChannels);
                                setActiveTvChannel(parsedChannels[0]);
                                setStreamUrl(formatStreamUrl(parsedChannels[0].url, parsedChannels[0].stream_type));
                                setStreamType(parsedChannels[0].stream_type || 'hls');
                                setLoadingStream(false);
                                return;
                            }
                        } catch (m3uErr) {
                            console.error("M3U Playlist parse error:", m3uErr);
                        }
                    }

                    const stType = (activeTvChannel && activeTvChannel.stream_type) || item.stream_type || 'hls';
                    setStreamUrl(formatStreamUrl(targetUrl, stType));
                    setStreamType(stType);
                    setLoadingStream(false);
                    return;
                }

                // --- ANILIST MEGAPLAY ---
                if (activeSource === 'anilist') {
                    const epNum = currentEpisode || 1;
                    const animeId = item.id;
                    const sourcesUrl = `${API_BASE}/api/anime/sources?episode_id=${epNum}&anime_id=${animeId}&category=${animeLanguage}`;
                    
                    const res = await fetch(sourcesUrl, { signal: abortController.signal });
                    const data = await res.json();
                    const sourceObj = data.url ? data : (data.data?.sources?.[0] || null);
                    
                    if (sourceObj && sourceObj.url) {
                        const proxyUrl = `${API_BASE}/api/iframe-proxy?url=${encodeURIComponent(sourceObj.url)}`;
                        setStreamUrl(proxyUrl);
                        setStreamType('embed');
                        setLoadingStream(false);
                        return;
                    } else {
                        throw new Error("Anime stream not found");
                    }
                }

                // --- MOVIEBOX / FALLBACK ---
                let url;
                let method = 'GET';
                if (activeSource === 'moviebox') {
                    method = 'POST';
                    url = `${API_BASE}/api/stream?mode=url&query=${encodeURIComponent(item.title)}`;
                    if (item.id) url += `&id=${encodeURIComponent(item.id)}`;
                    if (item.type) url += `&content_type=${encodeURIComponent(item.type)}`;
                    if (item.type !== 'movie' && currentSeason && currentEpisode) {
                        url += `&season=${currentSeason}&episode=${currentEpisode}`;
                    }
                } else {
                    const epId = fullDetails.episodeId || item.episodeId;
                    if (!epId) throw new Error("No episode ID found.");
                    url = `${API_BASE}/api/anime/sources?episode_id=${encodeURIComponent(epId)}&category=${animeLanguage}`;
                }

                const res = await fetch(url, { method, signal: abortController.signal });
                if (!res.ok) throw new Error(`Server error: ${res.status}`);
                const data = await res.json();

                if (activeSource === 'moviebox') {
                    if (data.status === 'success' && data.url) {
                        let finalUrl = data.url;
                        const isInternal = API_BASE ? finalUrl.includes(API_BASE) : finalUrl.includes(window.location.origin);
                        if (finalUrl.startsWith('http') && !isInternal) {
                            finalUrl = `${API_BASE}/api/proxy-stream?url=${encodeURIComponent(finalUrl)}`;
                        } else if (!finalUrl.startsWith('http')) {
                            finalUrl = `${API_BASE}${finalUrl}`;
                        }
                        setStreamUrl(finalUrl);
                        setStreamType(finalUrl.includes('.m3u8') ? 'hls' : 'mp4');
                        if (data.subtitles) {
                            setSubtitles(data.subtitles.map(s => ({
                                ...s,
                                url: s.url.startsWith('http') ? s.url : `${API_BASE}${s.url.startsWith('/') ? '' : '/'}${s.url}`
                            })));
                        }
                        setLoadingStream(false);
                    } else throw new Error(data.message || "Failed to get stream");
                } else {
                    if (data.url || (data.data && data.data.sources && data.data.sources.length > 0)) {
                        const s = data.url ? data : data.data.sources[0];
                        setStreamUrl(s.url);
                        setStreamType(s.type === 'embed' ? 'embed' : 'hls');
                        setLoadingStream(false);
                    } else throw new Error("Stream not found");
                }
            } catch (err) {
                if (err.name === 'AbortError') return;
                console.error("Stream Fetch Error:", err);
                if (retryCount < 1) {
                    console.log("[WatchPage] Retrying...");
                    setTimeout(() => fetchStream(retryCount + 1), 1000);
                } else {
                    setStreamError(err.message === 'signal is aborted' ? 'Request timed out' : err.message);
                    setLoadingStream(false);
                }
            }
        };

        fetchStream();

        return () => {
            abortController.abort();
            clearTimeout(timeoutId);
        };
    }, [currentSeason, currentEpisode, activeSource, item.id, item.type, API_BASE, fullDetails.episodeId, animeLanguage]);

    return (
        <div style={{ position: 'fixed', inset: 0, background: '#0a0a0f', zIndex: 2000, display: 'flex', flexDirection: 'column', color: '#fff', fontFamily: "'Inter', sans-serif" }}>
            <div style={{ height: '60px', padding: '0 1rem', borderBottom: '1px solid rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'rgba(10,10,15,0.95)', zIndex: 30, flexShrink: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', overflow: 'hidden', flex: 1 }}>
                    <button onClick={onBack} style={{ background: 'rgba(255,255,255,0.1)', border: 'none', color: 'white', padding: '0.5rem 1rem', borderRadius: '20px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.9rem', fontWeight: '500', flexShrink: 0 }}>
                        <span>←</span> Back
                    </button>
                    <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                        <span style={{ fontWeight: 'bold', fontSize: '1.2rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{item.title}</span>
                        <span style={{ fontSize: '1rem', color: '#6366f1', fontWeight: 'bold' }}>
                            {isTVChannel ? '🔴 Live' : isMovieContent ? 'Movie' : (activeSource === 'anilist' ? `Episode ${currentEpisode || 1}` : `S${currentSeason || 1} E${currentEpisode || 1}`)}
                        </span>
                    </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    {item.type !== 'movie' && (!isTVChannel || item.stream_type === 'm3u_playlist' || tvPlaylistChannels.length > 1) && (!isMobile || isSmartTV) && (
                        <button
                            onClick={() => setShowEpisodes(!showEpisodes)}
                            style={{
                                background: 'rgba(255,255,255,0.1)',
                                border: 'none',
                                color: 'white',
                                padding: '0.5rem 1rem',
                                borderRadius: '20px',
                                cursor: 'pointer',
                                fontSize: '0.9rem',
                                fontWeight: '500',
                                flexShrink: 0
                            }}
                        >
                            {isTVChannel 
                                ? (showEpisodes ? 'Hide Channels' : 'Show Channels')
                                : (showEpisodes ? 'Hide Episodes' : 'Show Episodes')}
                        </button>
                    )}
                </div>
            </div>

            <div style={{ flex: 1, display: 'flex', flexDirection: isMobile ? 'column' : 'row', overflow: 'hidden' }}>
                {/* Video Player Container */}
                <div style={{
                    flex: isMobile ? '0 0 auto' : 1,
                    width: isMobile ? '100%' : 'auto',
                    aspectRatio: isMobile ? '16/9' : 'auto',
                    height: isMobile ? 'auto' : '100%',
                    position: 'relative',
                    background: 'black',
                    zIndex: 20
                }}>
                    {loadingStream && (
                        <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(0,0,0,0.8)', zIndex: 10 }}>
                            <div style={{ width: '40px', height: '40px', border: '3px solid rgba(255,255,255,0.1)', borderTopColor: '#6366f1', borderRadius: '50%', animation: 'spin 1s linear infinite' }}></div>
                        </div>
                    )}
                    {streamError && (
                        <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: 'rgba(0,0,0,0.9)', zIndex: 11, padding: '20px', gap: '15px' }}>
                            <p style={{ color: '#ef4444', textAlign: 'center' }}>Play Error: {streamError}</p>
                            <div style={{ display: 'flex', gap: '10px' }}>
                                <button onClick={() => { setStreamError(null); setRetryCounter(c => c + 1); }} style={{ padding: '8px 16px', background: 'transparent', border: '1px solid #6366f1', color: '#6366f1', borderRadius: '8px', cursor: 'pointer', fontSize: '0.9rem' }}>Retry</button>
                                <button onClick={() => setShowManualInput(true)} style={{ padding: '8px 16px', background: 'transparent', border: '1px solid rgba(255,255,255,0.08)', color: 'white', borderRadius: '8px', cursor: 'pointer', fontSize: '0.9rem' }}>Enter ID</button>
                            </div>
                        </div>
                    )}
                    {streamUrl && (
                        <VideoPlayer
                            url={streamUrl}
                            type={streamType}
                            subtitles={subtitles}
                            title={item.title}
                            source={activeSource}
                            onClose={onBack}
                            autoPlay={true}
                            onNext={handleNextEpisode}
                            showNext={hasNext}
                            useVideoJS={isTVChannel ? true : useVideoJS}
                        />
                    )}
                </div>

                {/* Episode List / Sidebar */}
                {!isMovieContent && (!isTVChannel || item.stream_type === 'm3u_playlist' || tvPlaylistChannels.length > 1) && showEpisodes && (
                    <div style={{
                        width: isMobile ? '100%' : '320px',
                        flex: isMobile ? 1 : 'none',
                        background: '#121216',
                        borderLeft: isMobile ? 'none' : '1px solid rgba(255,255,255,0.05)',
                        display: 'flex',
                        flexDirection: 'column',
                        minHeight: 0 // Crucial for nested scrolling
                    }}>
                        <div style={{ padding: '1.5rem', borderBottom: '1px solid rgba(255,255,255,0.05)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <h3 style={{ margin: 0, fontSize: '1.1rem' }}>{isTVChannel ? 'Channels' : 'Episodes'}</h3>
                                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                                    {isTVChannel && tvPlaylistChannels.length > 0 && (
                                        <span style={{ fontSize: '0.75rem', color: '#888', background: 'rgba(255,255,255,0.05)', padding: '2px 8px', borderRadius: '10px' }}>
                                            {tvSearchQuery ? `${tvPlaylistChannels.filter(c => (c.title || c.name || '').toLowerCase().includes(tvSearchQuery.toLowerCase())).length} / ${tvPlaylistChannels.length}` : `${tvPlaylistChannels.length} channels`}
                                        </span>
                                    )}
                                    {activeSource === 'anilist' && (
                                        <div style={{ display: 'flex', background: 'rgba(255,255,255,0.05)', borderRadius: '8px', padding: '4px' }}>
                                            <button onClick={() => setAnimeLanguage('sub')} style={{ padding: '4px 8px', border: 'none', borderRadius: '4px', cursor: 'pointer', background: animeLanguage === 'sub' ? '#6366f1' : 'transparent', color: 'white', fontSize: '0.7rem' }}>SUB</button>
                                            <button onClick={() => setAnimeLanguage('dub')} style={{ padding: '4px 8px', border: 'none', borderRadius: '4px', cursor: 'pointer', background: animeLanguage === 'dub' ? '#6366f1' : 'transparent', color: 'white', fontSize: '0.7rem' }}>DUB</button>
                                        </div>
                                    )}
                                </div>
                            </div>

                            {isTVChannel && tvPlaylistChannels.length > 0 && (
                                <input
                                    type="text"
                                    placeholder="🔍 Search channels..."
                                    value={tvSearchQuery}
                                    onChange={(e) => setTvSearchQuery(e.target.value)}
                                    style={{
                                        marginTop: '4px',
                                        padding: '8px 12px',
                                        borderRadius: '8px',
                                        border: '1px solid rgba(255,255,255,0.1)',
                                        background: 'rgba(255,255,255,0.05)',
                                        color: 'white',
                                        fontSize: '0.85rem',
                                        outline: 'none',
                                        width: '100%',
                                        boxSizing: 'border-box'
                                    }}
                                />
                            )}

                            {/* Season Selector for MovieBox */}
                            {!isTVChannel && activeSource === 'moviebox' && seasonsData.length > 0 && (
                                <div style={{
                                    display: 'flex',
                                    gap: '8px',
                                    overflowX: 'auto',
                                    paddingBottom: '12px',
                                    marginTop: '8px',
                                    scrollbarWidth: 'thin',
                                    WebkitOverflowScrolling: 'touch',
                                    flexWrap: seasonsData.length > 6 ? 'wrap' : 'nowrap',
                                    maxHeight: seasonsData.length > 6 ? '120px' : 'auto',
                                    overflowY: 'auto'
                                }}>
                                    {seasonsData.map(s => (
                                        <button
                                            key={s.season_number}
                                            onClick={() => {
                                                if (currentSeason !== s.season_number) {
                                                    setStreamUrl(null); // Clear URL only when season actually changes
                                                    setCurrentSeason(s.season_number);
                                                    setCurrentEpisode(1);
                                                }
                                            }}
                                            style={{
                                                padding: '6px 14px',
                                                borderRadius: '16px',
                                                border: '1px solid ' + (currentSeason === s.season_number ? '#6366f1' : 'rgba(255,255,255,0.1)'),
                                                background: currentSeason === s.season_number ? '#6366f1' : 'rgba(255,255,255,0.05)',
                                                color: 'white',
                                                cursor: 'pointer',
                                                whiteSpace: 'nowrap',
                                                fontSize: '0.85rem',
                                                transition: 'all 0.2s'
                                            }}
                                        >
                                            S{s.season_number}
                                        </button>
                                    ))}
                                </div>
                            )}

                        </div>
                        {isTVChannel ? (
                            <div style={{ flex: 1, overflowY: 'auto', padding: '1rem', display: 'flex', flexDirection: 'column', gap: '8px', WebkitOverflowScrolling: 'touch', scrollbarWidth: 'thin' }}>
                                {(tvPlaylistChannels.length > 0 
                                    ? (tvSearchQuery ? tvPlaylistChannels.filter(c => (c.title || c.name || '').toLowerCase().includes(tvSearchQuery.toLowerCase())) : tvPlaylistChannels) 
                                    : [item]).map((chan, idx) => {
                                    const isActive = activeTvChannel && (activeTvChannel.url === chan.url || activeTvChannel.id === chan.id);
                                    return (
                                        <button
                                            key={chan.id || idx}
                                            onClick={() => {
                                                setActiveTvChannel(chan);
                                                const sType = chan.stream_type || 'hls';
                                                const finalUrl = formatStreamUrl(chan.url, sType);
                                                setStreamUrl(finalUrl);
                                                setStreamType(sType);
                                            }}
                                            title={chan.title || chan.name}
                                            style={{
                                                padding: '10px 14px',
                                                borderRadius: '8px',
                                                border: '1px solid ' + (isActive ? '#6366f1' : 'rgba(255,255,255,0.08)'),
                                                background: isActive ? 'rgba(99, 102, 241, 0.2)' : 'rgba(255,255,255,0.03)',
                                                color: 'white',
                                                cursor: 'pointer',
                                                textAlign: 'left',
                                                fontSize: '0.9rem',
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: '10px',
                                                width: '100%',
                                                minWidth: 0,
                                                boxSizing: 'border-box'
                                            }}
                                        >
                                            {chan.poster_url && <img src={chan.poster_url} alt="" style={{ width: '24px', height: '24px', objectFit: 'contain', borderRadius: '4px', flexShrink: 0 }} onError={(e) => e.target.style.display = 'none'} />}
                                            <span style={{ flex: 1, minWidth: 0, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{chan.title || chan.name || `Channel ${idx + 1}`}</span>
                                        </button>
                                    );
                                })}
                            </div>
                        ) : (
                            <div style={{ flex: 1, overflowY: 'auto', padding: '1rem', display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(60px, 1fr))', gap: '8px' }}>
                                {activeSource === 'anilist' ? (
                                    animeEpisodes.map(ep => (
                                        <button
                                            key={ep.episodeId}
                                            onClick={() => {
                                                if (currentEpisode !== ep.number) {
                                                    setStreamUrl(null); // Clear URL only when episode actually changes
                                                    setFullDetails(prev => ({ ...prev, episodeId: ep.episodeId }));
                                                    setCurrentEpisode(ep.number);
                                                }
                                            }}
                                            style={{ padding: '12px 8px', borderRadius: '8px', border: '1px solid ' + (currentEpisode === ep.number ? '#6366f1' : 'rgba(255,255,255,0.1)'), background: currentEpisode === ep.number ? 'rgba(99, 102, 241, 0.1)' : 'transparent', color: 'white', cursor: 'pointer' }}
                                        >
                                            {ep.number}
                                        </button>
                                    ))
                                ) : (
                                    Array.from({ length: getMaxEpisodes() }, (_, i) => i + 1).map(ep => (
                                        <button
                                            key={ep}
                                            onClick={() => {
                                                if (currentEpisode !== ep) {
                                                    setStreamUrl(null); // Clear URL only when episode actually changes
                                                    setCurrentEpisode(ep);
                                                }
                                            }}
                                            style={{ padding: '12px 8px', borderRadius: '8px', border: '1px solid ' + (currentEpisode === ep ? '#6366f1' : 'rgba(255,255,255,0.1)'), background: currentEpisode === ep ? 'rgba(99, 102, 241, 0.1)' : 'transparent', color: 'white', cursor: 'pointer' }}
                                        >
                                            {ep}
                                        </button>
                                    ))
                                )}
                            </div>
                        )}
                    </div>
                )}
            </div>
            <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
    );
};

export default WatchPage;
