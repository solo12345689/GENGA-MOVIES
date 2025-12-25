import React, { useState, useEffect, useRef } from 'react';
import VideoPlayer from './VideoPlayer';

const WatchPage = ({ item, initialSeason, initialEpisode, API_BASE, onBack }) => {
    // State
    const [currentSeason, setCurrentSeason] = useState(initialSeason || (item.type === 'movie' ? null : 1));
    const [currentEpisode, setCurrentEpisode] = useState(initialEpisode || (item.type === 'movie' ? null : 1));
    const [streamUrl, setStreamUrl] = useState(null);
    const [loadingStream, setLoadingStream] = useState(false);
    const [seasonsData, setSeasonsData] = useState([]); // Store full season objects
    const [streamError, setStreamError] = useState(null);
    const [fullDetails, setFullDetails] = useState(item); // Start with passed item, update with fetch
    const [loadingDetails, setLoadingDetails] = useState(false);

    // Mobile Repsonsiveness
    const [isMobile, setIsMobile] = useState(window.innerWidth <= 1024);

    // Performance: Pre-fetch Cache
    const prefetchCache = useRef({});

    useEffect(() => {
        const handleResize = () => setIsMobile(window.innerWidth <= 1024);
        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, []);

    // Helper to get max episodes for current season
    const getMaxEpisodes = (seasonNum = currentSeason) => {
        if (!seasonsData.length) return 24; // Default fallback
        const seasonObj = seasonsData.find(s => s.season_number === seasonNum);
        return seasonObj ? seasonObj.max_episodes : 24;
    };

    // Calculate Next Episode
    const getNextEpisode = () => {
        if (fullDetails.type === 'movie') return null;

        const maxEp = getMaxEpisodes(currentSeason);
        if (currentEpisode < maxEp) {
            return { season: currentSeason, episode: currentEpisode + 1 };
        } else {
            // Check next season
            const nextSeasonNum = currentSeason + 1;
            const nextSeasonExists = seasonsData.some(s => s.season_number === nextSeasonNum);
            if (nextSeasonExists) {
                return { season: nextSeasonNum, episode: 1 };
            }
        }
        return null;
    };

    const hasNext = !!getNextEpisode();

    const handleNextEpisode = () => {
        const next = getNextEpisode();
        if (next) {
            setCurrentSeason(next.season);
            setCurrentEpisode(next.episode);
        }
    };

    // Fetch Full Details (for seasons/episodes) if needed
    useEffect(() => {
        const fetchDetails = async () => {
            if (item.type === 'series' || item.type === 'anime') {
                // Always fetch details to get accurate episode counts per season
                setLoadingDetails(true);
                try {
                    const res = await fetch(`${API_BASE}/api/details/${item.id}`);
                    const data = await res.json();
                    setFullDetails({ ...item, ...data });

                    if (data.seasons && Array.isArray(data.seasons)) {
                        // Backend returns [{ season_number: 1, max_episodes: 20 }, ...]
                        setSeasonsData(data.seasons);

                        // If no current season set, default to first available
                        if (!currentSeason && data.seasons.length > 0) {
                            setCurrentSeason(data.seasons[0].season_number);
                            setCurrentEpisode(1);
                        }
                    } else if (item.seasons) {
                        // Fallback if only count is known (create generic objects)
                        const count = typeof item.seasons === 'number' ? item.seasons : 1;
                        const genericSeasons = Array.from({ length: count }, (_, i) => ({
                            season_number: i + 1,
                            max_episodes: 24 // Fallback count
                        }));
                        setSeasonsData(genericSeasons);
                    } else {
                        // Absolute fallback
                        setSeasonsData([{ season_number: 1, max_episodes: 24 }]);
                    }
                } catch (err) {
                    console.error("Failed to fetch details for WatchPage", err);
                    setSeasonsData([{ season_number: 1, max_episodes: 24 }]);
                } finally {
                    setLoadingDetails(false);
                }
            }
        };
        fetchDetails();
    }, [item, API_BASE]);

    // Fetch Stream URL
    useEffect(() => {
        const fetchStream = async () => {
            setLoadingStream(true);
            setStreamError(null);
            setStreamUrl(null); // Reset URL to prevent old video playing

            // Check Cache First
            const cacheKey = `s${currentSeason}e${currentEpisode}`;
            if (prefetchCache.current[cacheKey]) {
                console.log("Using pre-fetched stream:", cacheKey);
                setStreamUrl(prefetchCache.current[cacheKey]);
                setLoadingStream(false);
                return;
            }

            try {
                let url = `${API_BASE}/api/stream?mode=url&query=${encodeURIComponent(item.title)}`;

                if (item.id) {
                    url += `&id=${encodeURIComponent(item.id)}`;
                }

                if (item.type) {
                    url += `&content_type=${encodeURIComponent(item.type)}`;
                }

                if (fullDetails.type !== 'movie' && currentSeason && currentEpisode) {
                    url += `&season=${currentSeason}&episode=${currentEpisode}`;
                }

                console.log("Fetching stream from:", url);
                const res = await fetch(url, { method: 'POST' });
                const data = await res.json();

                if (data.status === 'success' && data.url) {
                    const finalUrl = data.url.startsWith('http') ? data.url : `${API_BASE}${data.url}`;
                    setStreamUrl(finalUrl);
                    // Cache it specifically for current
                    prefetchCache.current[cacheKey] = finalUrl;
                } else {
                    setStreamError(data.message || "Failed to resolve stream");
                }
            } catch (err) {
                console.error(err);
                setStreamError("Network error while resolving stream");
            } finally {
                setLoadingStream(false);
            }
        };

        // Debounce slightly to prevent rapid firing if user clicks fast, 
        // UNLESS we have it cached (logic handled inside)
        const timeoutId = setTimeout(fetchStream, 100);
        return () => clearTimeout(timeoutId);
    }, [item, currentSeason, currentEpisode, API_BASE, fullDetails.type]);

    // Pre-fetch Logic (Effect)
    useEffect(() => {
        if (!streamUrl || loadingStream) return; // Only prefetch if current is ready

        const prefetchNext = async () => {
            const next = getNextEpisode();
            if (!next) return;

            const cacheKey = `s${next.season}e${next.episode}`;
            if (prefetchCache.current[cacheKey]) return; // Already cached

            console.log("Pre-fetching next episode:", cacheKey);

            try {
                let url = `${API_BASE}/api/stream?mode=url&query=${encodeURIComponent(item.title)}`;
                if (item.id) url += `&id=${encodeURIComponent(item.id)}`;
                if (item.type) url += `&content_type=${encodeURIComponent(item.type)}`;
                url += `&season=${next.season}&episode=${next.episode}`;

                const res = await fetch(url, { method: 'POST' });
                const data = await res.json();

                if (data.status === 'success' && data.url) {
                    const finalUrl = data.url.startsWith('http') ? data.url : `${API_BASE}${data.url}`;
                    prefetchCache.current[cacheKey] = finalUrl;
                    console.log("Pre-fetch successful:", cacheKey);
                }
            } catch (ignore) {
                // Silent fail for prefetch
                console.warn("Pre-fetch failed silent:", ignore);
            }
        };

        const timer = setTimeout(prefetchNext, 3000); // Start prefetch 3s after current video loads
        return () => clearTimeout(timer);
    }, [streamUrl, currentSeason, currentEpisode, loadingStream]);


    return (
        <div style={{
            position: 'fixed',
            inset: 0,
            background: '#0a0a0f', // Darker background
            zIndex: 200,
            display: 'flex',
            flexDirection: 'column',
            color: '#fff',
            fontFamily: "'Inter', sans-serif"
        }}>
            {/* Header */}
            <div style={{
                height: '60px',
                padding: '0 2rem',
                borderBottom: '1px solid rgba(255,255,255,0.1)',
                display: 'flex',
                alignItems: 'center',
                background: 'rgba(10,10,15,0.95)',
                zIndex: 30
            }}>
                <button
                    onClick={onBack}
                    style={{
                        background: 'rgba(255,255,255,0.1)',
                        border: 'none',
                        color: 'white',
                        padding: '0.5rem 1rem',
                        borderRadius: '20px',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        fontSize: '0.9rem',
                        fontWeight: '500'
                    }}
                >
                    <span>←</span> Back
                </button>
                <div style={{ marginLeft: '1.5rem', display: 'flex', flexDirection: 'column' }}>
                    <span style={{ fontWeight: '600', fontSize: '1rem' }}>{item.title}</span>
                    {fullDetails.type !== 'movie' && (
                        <span style={{ fontSize: '0.8rem', color: '#9ca3af' }}>
                            Season {currentSeason} • Episode {currentEpisode}
                        </span>
                    )}
                </div>
            </div>

            {/* Main Content Area */}
            <div style={{
                flex: 1,
                display: 'flex',
                flexDirection: isMobile ? 'column' : 'row',
                overflow: 'hidden'
            }}>

                {/* Left: Video Player (Takes most space) */}
                <div style={{
                    flex: isMobile ? '0 0 auto' : 1,
                    height: isMobile ? 'auto' : '100%',
                    aspectRatio: isMobile ? '16/9' : 'auto',
                    position: 'relative',
                    background: 'black',
                    display: 'flex',
                    alignItems: 'center',
                    justifyItems: 'center'
                }}>

                    {/* Loading State */}
                    {loadingStream && (
                        <div style={{
                            position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column',
                            alignItems: 'center', justifyContent: 'center', zIndex: 10
                        }}>
                            <div className="spinner" style={{
                                width: '50px', height: '50px',
                                border: '3px solid rgba(255,255,255,0.1)',
                                borderTopColor: '#6366f1',
                                borderRadius: '50%',
                                animation: 'spin 1s linear infinite',
                                marginBottom: '1.5rem'
                            }}></div>
                            <p style={{ color: '#9ca3af', fontSize: '0.9rem' }}>Resolving Stream...</p>
                        </div>
                    )}

                    {/* Error State */}
                    {!loadingStream && streamError && (
                        <div style={{
                            position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column',
                            alignItems: 'center', justifyContent: 'center', zIndex: 10,
                            background: 'rgba(0,0,0,0.8)'
                        }}>
                            <span style={{ fontSize: '3rem', marginBottom: '1rem' }}>⚠️</span>
                            <p style={{ color: '#ef4444', marginBottom: '1rem' }}>{streamError}</p>
                            <button
                                onClick={() => setLoadingStream(true)} // Trigger re-fecth logic potentially
                                style={{
                                    padding: '0.5rem 1.5rem',
                                    background: '#6366f1',
                                    border: 'none',
                                    color: 'white',
                                    borderRadius: '8px',
                                    cursor: 'pointer'
                                }}
                            >
                                Retry
                            </button>
                        </div>
                    )}

                    {/* Video Player Component */}
                    {!loadingStream && !streamError && streamUrl && (
                        <VideoPlayer
                            url={streamUrl}
                            title={fullDetails.type === 'movie' ? item.title : `S${currentSeason} E${currentEpisode} - ${item.title}`}
                            onClose={onBack}
                            autoPlay={true}
                            onNext={handleNextEpisode}
                            showNext={hasNext}
                        />
                    )}
                </div>

                {/* Right: Sidebar (Only for Series/Anime) */}
                {fullDetails.type !== 'movie' && (
                    <div style={{
                        width: isMobile ? '100%' : '320px',
                        flex: isMobile ? 1 : 'none',
                        background: '#121216',
                        borderLeft: isMobile ? 'none' : '1px solid rgba(255,255,255,0.05)',
                        borderTop: isMobile ? '1px solid rgba(255,255,255,0.05)' : 'none',
                        display: 'flex',
                        flexDirection: 'column'
                    }}>
                        <div style={{ padding: '1.5rem 1.5rem 1rem', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                            <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: '600' }}>Episodes</h3>
                            <p style={{ margin: '0.5rem 0 0', fontSize: '0.85rem', color: '#9ca3af' }}>
                                Select an episode to play
                            </p>
                        </div>

                        {/* Season Tabs - Premium Scrollable Look */}
                        <div style={{
                            padding: '1rem 1.5rem',
                            display: 'flex',
                            gap: '0.5rem',
                            overflowX: 'auto',
                            borderBottom: '1px solid rgba(255,255,255,0.05)'
                        }}>
                            {/* If seasonsData is populated, use it. Otherwise 1 button */}
                            {seasonsData.length > 0 ? seasonsData.map(sId => (
                                <button
                                    key={sId.season_number}
                                    onClick={() => { setCurrentSeason(sId.season_number); setCurrentEpisode(1); }}
                                    style={{
                                        background: currentSeason === sId.season_number ? 'rgba(99, 102, 241, 0.2)' : 'transparent',
                                        border: '1px solid',
                                        borderColor: currentSeason === sId.season_number ? '#6366f1' : 'rgba(255,255,255,0.1)',
                                        color: currentSeason === sId.season_number ? '#818cf8' : '#9ca3af',
                                        padding: '0.4rem 0.8rem',
                                        borderRadius: '6px',
                                        cursor: 'pointer',
                                        fontSize: '0.85rem',
                                        whiteSpace: 'nowrap',
                                        transition: 'all 0.2s'
                                    }}
                                >
                                    Season {sId.season_number}
                                </button>
                            )) : (
                                <p style={{ color: 'gray' }}>Loading...</p>
                            )}
                        </div>

                        {/* Episode Grid - Clean Look */}
                        <div style={{ flex: 1, overflowY: 'auto', padding: '1.5rem' }}>
                            <div style={{
                                display: 'grid',
                                gridTemplateColumns: 'repeat(auto-fill, minmax(50px, 1fr))',
                                gap: '0.8rem'
                            }}>
                                {Array.from({ length: getMaxEpisodes() }, (_, i) => i + 1).map(ep => (
                                    <button
                                        key={ep}
                                        onClick={() => setCurrentEpisode(ep)}
                                        style={{
                                            aspectRatio: '1',
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'center',
                                            background: (currentSeason === currentSeason && currentEpisode === ep)
                                                ? '#6366f1'
                                                : 'rgba(255,255,255,0.03)',
                                            border: 'none',
                                            borderRadius: '8px',
                                            color: 'white',
                                            fontWeight: (currentSeason === currentSeason && currentEpisode === ep) ? '600' : '400',
                                            cursor: 'pointer',
                                            transition: 'transform 0.2s, background 0.2s'
                                        }}
                                        onMouseEnter={e => {
                                            if (currentEpisode !== ep) e.target.style.background = 'rgba(255,255,255,0.08)';
                                        }}
                                        onMouseLeave={e => {
                                            if (currentEpisode !== ep) e.target.style.background = 'rgba(255,255,255,0.03)';
                                        }}
                                    >
                                        {ep}
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>
                )}
            </div>

            <style>{`
                ::-webkit-scrollbar { width: 6px; height: 6px; }
                ::-webkit-scrollbar-track { background: transparent; }
                ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); borderRadius: 3px; }
                ::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.2); }
                @keyframes spin { to { transform: rotate(360deg); } }
            `}</style>
        </div>
    );
};

export default WatchPage;
