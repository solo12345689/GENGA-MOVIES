import React, { useRef, useEffect, useState } from 'react';

// ─── YouTube IFrame API Player ────────────────────────────────────────────────
// Uses the official YT.Player API (same as Famelack) instead of raw <iframe>.
// The IFrame API correctly sets: origin=window.location.origin & enablejsapi=1,
// which allows playing channels that Error 153 blocks in plain embeds.
const YouTubeIframePlayer = ({ url, source }) => {
    const containerRef = useRef(null);
    const playerRef = useRef(null);
    const [fallback, setFallback] = useState(false);

    // Extract video ID from embed URL: /embed/VIDEO_ID
    const videoId = url && url.match(/\/embed\/([A-Za-z0-9_-]{6,})/)?.[1];
    // Build watch URL for open-in-youtube button
    const watchUrl = videoId ? `https://www.youtube.com/watch?v=${videoId}` : url;

    useEffect(() => {
        if (!videoId || !containerRef.current) {
            setFallback(true);
            return;
        }

        let isMounted = true;
        let timeoutId = null;

        const initPlayer = () => {
            if (!isMounted || !containerRef.current) return;
            try {
                playerRef.current = new window.YT.Player(containerRef.current, {
                    videoId,
                    width: '100%',
                    height: '100%',
                    playerVars: {
                        autoplay: 1,
                        rel: 0,
                        playsinline: 1,
                        enablejsapi: 1,
                        modestbranding: 1,
                        origin: window.location.origin,
                    },
                    events: {
                        onReady: (e) => {
                            if (isMounted) e.target.playVideo();
                        },
                        onError: (e) => {
                            // Error 150/153: embedding not allowed — show fallback
                            console.warn('[YouTubeIframePlayer] YT error code:', e.data);
                            if (isMounted) setFallback(true);
                        },
                    },
                });
            } catch (err) {
                console.error('[YouTubeIframePlayer] Failed to init YT.Player:', err);
                if (isMounted) setFallback(true);
            }
        };

        if (window.YT && window.YT.Player) {
            initPlayer();
        } else {
            // Load the IFrame API script if not already loaded
            if (!document.getElementById('yt-iframe-api')) {
                const script = document.createElement('script');
                script.id = 'yt-iframe-api';
                script.src = 'https://www.youtube.com/iframe_api';
                script.onerror = () => { if (isMounted) setFallback(true); };
                document.head.appendChild(script);
            }
            // Timeout fallback if API never loads
            timeoutId = setTimeout(() => {
                if (isMounted && !window.YT) setFallback(true);
            }, 5000);
            // Poll for YT ready
            const poll = setInterval(() => {
                if (window.YT && window.YT.Player) {
                    clearInterval(poll);
                    clearTimeout(timeoutId);
                    initPlayer();
                }
            }, 200);
        }

        return () => {
            isMounted = false;
            clearTimeout(timeoutId);
            if (playerRef.current && playerRef.current.destroy) {
                try { playerRef.current.destroy(); } catch { }
            }
        };
    }, [videoId]);

    if (fallback) {
        // Error 153 / API failed — show a proper error screen with YouTube link
        return (
            <div style={{ position: 'relative', width: '100%', height: '100%', background: '#0f0f0f', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 16 }}>
                <svg width="64" height="64" viewBox="0 0 24 24" fill="#ff0000"><path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-5.77 0 2.89 2.89 0 0 1 2.89-2.89c.28 0 .54.04.79.1V9.01a6.34 6.34 0 0 0-6.34 6.34 6.34 6.34 0 0 0 12.67 0l-.04-8.41a8.16 8.16 0 0 0 4.77 1.52V5.01a4.85 4.85 0 0 1-1-1.68z" /></svg>
                <p style={{ color: '#fff', fontWeight: 700, fontSize: '1.1rem', margin: 0 }}>Embedding disabled by channel</p>
                <p style={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.85rem', margin: 0 }}>This channel has restricted embedding. Watch directly on YouTube.</p>
                <a href={watchUrl} target="_blank" rel="noopener noreferrer"
                    style={{ display: 'flex', alignItems: 'center', gap: 8, background: '#ff0000', color: '#fff', padding: '12px 24px', borderRadius: 24, fontWeight: 700, fontSize: '1rem', textDecoration: 'none', marginTop: 8 }}>
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="white"><path d="M21.58 7.19c-.23-.86-.91-1.54-1.77-1.77C18.25 5 12 5 12 5s-6.25 0-7.81.42c-.86.23-1.54.91-1.77 1.77C2 8.75 2 12 2 12s0 3.25.42 4.81c.23.86.91 1.54 1.77 1.77C5.75 19 12 19 12 19s6.25 0 7.81-.42c.86-.23 1.54-.91 1.77-1.77C22 15.25 22 12 22 12s0-3.25-.42-4.81zM10 15V9l6 3-6 3z" /></svg>
                    Watch on YouTube
                </a>
            </div>
        );
    }

    return (
        <div style={{ width: '100%', height: '100%' }}>
            <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
        </div>
    );
};

const VideoPlayer = ({ url, type = 'hls', title, subtitles = [], onClose, onNext, showNext, autoPlay = true, source = 'moviebox' }) => {
    const videoRef = useRef(null);
    const [isPlaying, setIsPlaying] = useState(autoPlay);
    const [isBuffering, setIsBuffering] = useState(true);
    const [progress, setProgress] = useState(0);
    const [buffered, setBuffered] = useState(0);
    const [bufferedSeconds, setBufferedSeconds] = useState(0);
    const [volume, setVolume] = useState(1);
    const [showControls, setShowControls] = useState(true);
    const controlsTimeoutRef = useRef(null);
    const [isFullscreen, setIsFullscreen] = useState(false);
    const playerContainerRef = useRef(null);
    const [currentTime, setCurrentTime] = useState(0);
    const [duration, setDuration] = useState(0);
    const [showSubtitleMenu, setShowSubtitleMenu] = useState(false);
    const [subtitlesEnabled, setSubtitlesEnabled] = useState(() => {
        if (source === 'moviebox') {
            const saved = localStorage.getItem('moviebox_subtitles_enabled');
            return saved !== 'false'; // Defaults to true if null/undefined, otherwise respects 'false'
        }
        return true; // Default for other sources
    });
    const [selectedSubtitle, setSelectedSubtitle] = useState(0);
    const [subtitleSearch, setSubtitleSearch] = useState('');
    const [preferredLang, setPreferredLang] = useState(localStorage.getItem('preferred_subtitle_lang') || 'English');

    // FIX 1: Add a ref to track if the user is using touch (Mobile)
    const isTouch = useRef(false);

    // Unified source loading effect
    useEffect(() => {
        const video = videoRef.current;
        if (!video || type === 'embed' || !url) return;

        // --- HLS and Standard Source Setup ---
        const safePlay = () => {
            if (autoPlay && video.paused) {
                const playPromise = video.play();
                if (playPromise !== undefined) {
                    playPromise.catch(error => {
                        // Suppress AbortError (interrupted by new load) and generic autoplay blocks
                        if (error.name !== 'AbortError') {
                            console.log("[VideoPlayer] Autoplay prevented or interrupted:", error.message);
                        }
                    });
                }
            }
        };

        const setupSource = () => {
            if (url.includes('.m3u8')) {
                if (video.canPlayType('application/vnd.apple.mpegurl')) {
                    // Safari native HLS
                    video.src = url;
                    safePlay();
                } else if (window.Hls && window.Hls.isSupported()) {
                    hls = new window.Hls({
                        enableWorker: true,
                        startFragPrefetch: true,
                        lowLatencyMode: true,
                        liveSyncDuration: 1,
                        liveMaxLatencyDuration: 3,
                        maxBufferLength: 6,
                        maxMaxBufferLength: 10,
                        manifestLoadingRetryDelay: 500,
                        levelLoadingRetryDelay: 500,
                    });
                    hls.loadSource(url);
                    hls.attachMedia(video);
                    hls.on(window.Hls.Events.MANIFEST_PARSED, () => {
                        safePlay();
                    });
                    hls.on(window.Hls.Events.ERROR, (event, data) => {
                        if (data.fatal) {
                            if (data.type === window.Hls.ErrorTypes.NETWORK_ERROR) {
                                hls.startLoad();
                            } else {
                                hls.destroy();
                            }
                        }
                    });
                } else {
                    const script = document.createElement('script');
                    script.src = "https://cdn.jsdelivr.net/npm/hls.js@latest";
                    script.onload = () => {
                        const Hls = window.Hls;
                        if (Hls.isSupported()) {
                            hls = new Hls({
                                enableWorker: true,
                                startFragPrefetch: true,
                                lowLatencyMode: true,
                                liveSyncDuration: 1,
                                maxBufferLength: 6
                            });
                            hls.loadSource(url);
                            hls.attachMedia(video);
                            hls.on(Hls.Events.MANIFEST_PARSED, () => safePlay());
                        } else {
                            video.src = url;
                            safePlay();
                        }
                    };
                    document.head.appendChild(script);
                }

            } else {
                video.src = url;
                safePlay();
            }
        };

        setupSource();

        return () => {
            if (hls) hls.destroy();
        };
    }, [url, type, autoPlay]);

    // Subtitle track control effect
    useEffect(() => {
        const video = videoRef.current;
        if (!video || !video.textTracks) return;

        const timeout = setTimeout(() => {
            for (let i = 0; i < video.textTracks.length; i++) {
                const track = video.textTracks[i];
                if (!subtitlesEnabled) {
                    track.mode = 'disabled';
                } else {
                    // Match by label for robustness
                    const isSelected = track.label === preferredLang;
                    track.mode = isSelected ? 'showing' : 'hidden';
                }
            }
        }, 150); // Slightly more delay for track mounting
        return () => clearTimeout(timeout);
    }, [subtitlesEnabled, preferredLang, subtitles, url]);

    // Save MovieBox subtitle preference
    useEffect(() => {
        if (source === 'moviebox') {
            localStorage.setItem('moviebox_subtitles_enabled', subtitlesEnabled);
        }
    }, [subtitlesEnabled, source]);

    // Handle initial subtitle selection based on preference
    useEffect(() => {
        if (subtitles && subtitles.length > 0) {
            const hasMatch = subtitles.some(s => s.lang.toLowerCase() === preferredLang.toLowerCase());
            if (!hasMatch) {
                // If preferred lang not found, default to English or first available
                const fallback = subtitles.find(s => s.lang.toLowerCase() === 'english') || subtitles[0];
                if (fallback) setPreferredLang(fallback.lang);
            }
        }
    }, [subtitles]);

    // Separate effect for event listeners and progress tracking
    useEffect(() => {
        const video = videoRef.current;
        if (!video || type === 'embed') return;

        const updateProgress = () => {
            if (video.duration) {
                setCurrentTime(video.currentTime);
                setDuration(video.duration);
                setProgress((video.currentTime / video.duration) * 100);

                if (video.buffered.length > 0) {
                    for (let i = 0; i < video.buffered.length; i++) {
                        if (video.buffered.start(i) <= video.currentTime && video.buffered.end(i) >= video.currentTime) {
                            const end = video.buffered.end(i);
                            setBuffered((end / video.duration) * 100);
                            setBufferedSeconds(Math.floor(end - video.currentTime));
                            break;
                        }
                    }
                }
            }
        };

        const handlePlay = () => {
            setIsPlaying(true);
            setIsBuffering(false);
        };

        const handlePause = () => {
            setIsPlaying(false);
            setIsBuffering(false);
        };

        const handleWaiting = () => setIsBuffering(true);
        const handleCanPlay = () => setIsBuffering(false);
        const handlePlaying = () => setIsBuffering(false);
        const handleEnded = () => {
            setShowControls(true);
        };

        video.addEventListener('timeupdate', updateProgress);
        video.addEventListener('progress', updateProgress);
        video.addEventListener('play', handlePlay);
        video.addEventListener('pause', handlePause);
        video.addEventListener('waiting', handleWaiting);
        video.addEventListener('canplay', handleCanPlay);
        video.addEventListener('playing', handlePlaying);
        video.addEventListener('ended', handleEnded);

        return () => {
            video.removeEventListener('timeupdate', updateProgress);
            video.removeEventListener('progress', updateProgress);
            video.removeEventListener('play', handlePlay);
            video.removeEventListener('pause', handlePause);
            video.removeEventListener('waiting', handleWaiting);
            video.removeEventListener('canplay', handleCanPlay);
            video.removeEventListener('playing', handlePlaying);
            video.removeEventListener('ended', handleEnded);
        };
    }, [type]); // Event listeners only depend on the type of player


    const resetControlsTimeout = () => {
        setShowControls(true);
        if (controlsTimeoutRef.current) clearTimeout(controlsTimeoutRef.current);
        controlsTimeoutRef.current = setTimeout(() => {
            if (isPlaying) setShowControls(false);
        }, 2500);
    };

    // FIX 2: Update Mouse/Touch handlers to set the isTouch flag
    const handleMouseMove = () => {
        isTouch.current = false; // We are on Desktop/Mouse
        resetControlsTimeout();
    };

    const handleTouchStart = () => {
        isTouch.current = true; // We are on Mobile/Touch
        if (!showControls) {
            setShowControls(true);
            if (controlsTimeoutRef.current) clearTimeout(controlsTimeoutRef.current);
            controlsTimeoutRef.current = setTimeout(() => {
                if (isPlaying) setShowControls(false);
            }, 3000);
        } else {
            resetControlsTimeout();
        }
    };

    const togglePlay = (e) => {
        if (e) e.stopPropagation();
        if (videoRef.current) {
            if (isPlaying) videoRef.current.pause();
            else videoRef.current.play();
        }
    };

    const handleSeek = (e) => {
        if (e) e.stopPropagation(); // Stop bubbling
        if (videoRef.current && Number.isFinite(videoRef.current.duration)) {
            const seekTime = (e.target.value / 100) * videoRef.current.duration;
            if (Number.isFinite(seekTime)) {
                videoRef.current.currentTime = seekTime;
                setProgress(e.target.value);
            }
        }
    };

    // FIX 3: Update Fullscreen logic to handle iOS Safari
    const toggleFullscreen = (e) => {
        if (e) e.stopPropagation(); // Prevent clicks from bubbling

        const container = playerContainerRef.current;
        const video = videoRef.current;

        if (!document.fullscreenElement) {
            // Standard Desktop/Android
            if (container.requestFullscreen) {
                container.requestFullscreen().catch(err => {
                    console.error(`Error attempting to enable fullscreen: ${err.message}`);
                });
                setIsFullscreen(true);
            }
            // iOS Safari Fallback
            else if (video.webkitEnterFullscreen) {
                video.webkitEnterFullscreen();
            }
        } else {
            if (document.exitFullscreen) {
                document.exitFullscreen();
                setIsFullscreen(false);
            }
        }
    };

    const formatTime = (seconds) => {
        if (!isFinite(seconds) || isNaN(seconds) || seconds <= 0) return '--:--';
        const min = Math.floor(seconds / 60);
        const sec = Math.floor(seconds % 60);
        return `${min}:${sec < 10 ? '0' : ''}${sec}`;
    };

    // Detect live stream by checking if duration is Infinity or source is TV
    const isLiveStream = !isFinite(duration) || source === 'tv';

    return (
        <div
            ref={playerContainerRef}
            className="video-player-container"
            onMouseMove={handleMouseMove}
            onTouchStart={handleTouchStart}
            // FIX 4: Only hide controls on mouse leave if NOT using touch
            onMouseLeave={() => {
                if (isPlaying && !isTouch.current) {
                    setShowControls(false);
                }
            }}
            style={{
                width: '100%',
                height: '100%',
                backgroundColor: '#000',
                position: 'relative',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                overflow: 'hidden',
                fontFamily: 'monospace'
            }}
        >
            {type === 'embed' ? (
                (url && (url.includes('youtube.com') || url.includes('youtu.be'))) ? (
                    <YouTubeIframePlayer url={url} source={source} />
                ) : (
                    <iframe
                        src={url}
                        style={{ width: '100%', height: '100%', border: 'none' }}
                        allowFullScreen
                        allow="autoplay; fullscreen; encrypted-media; picture-in-picture"
                        frameBorder="0"
                        scrolling="no"
                        title="Video Player"
                    />
                )
            ) : (
                <video
                    ref={videoRef}
                    style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                    onClick={togglePlay}
                    onDoubleClick={toggleFullscreen}
                    playsInline
                    preload="auto"
                    {...(source === 'moviebox' ? { crossOrigin: 'anonymous' } : {})}
                    onError={(e) => {
                        const error = videoRef.current?.error;
                        console.error("[VideoPlayer] Video element error:", error?.message || error);
                        // Do NOT alert — live TV streams frequently get CORS/geo errors
                    }}
                >
                    {subtitles.map((sub, idx) => (
                        <track
                            key={`${idx}-${sub.lang}`}
                            kind="subtitles"
                            label={sub.lang}
                            srcLang={sub.lang.toLowerCase().substring(0, 2)}
                            src={sub.url}
                            default={sub.lang === preferredLang}
                        />
                    ))}
                </video>
            )}

            {/* Buffering Indicator */}
            {isBuffering && type !== 'embed' && (
                <div style={{
                    position: 'absolute', inset: 0,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    background: 'rgba(0,0,0,0.1)',
                    zIndex: 2, pointerEvents: 'none'
                }}>
                    <div className="spinner" style={{
                        width: '50px', height: '50px',
                        border: '4px solid rgba(255,255,255,0.3)',
                        borderTopColor: '#fff',
                        borderRadius: '50%',
                        animation: 'spin 1s linear infinite'
                    }}></div>
                </div>
            )}

            {/* Click to Play Overlay (if paused) */}
            {!isPlaying && !isBuffering && type !== 'embed' && currentTime > 0 && (
                <div
                    onClick={togglePlay}
                    style={{
                        position: 'absolute', inset: 0,
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        background: 'rgba(0,0,0,0.3)', cursor: 'pointer', zIndex: 1
                    }}
                >
                    <div style={{
                        width: '80px', height: '80px', borderRadius: '50%',
                        background: 'rgba(0,0,0,0.6)', border: '2px solid rgba(255,255,255,0.2)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        color: 'white', fontSize: '2rem', paddingLeft: '5px'
                    }}>
                        ▶
                    </div>
                </div>
            )}

            {/* Top Bar (Hidden for embeds) */}
            {type !== 'embed' && (
                <div style={{
                    position: 'absolute', top: 0, left: 0, right: 0,
                    padding: '1rem 2rem',
                    background: 'linear-gradient(to bottom, rgba(0,0,0,0.8) 0%, transparent 100%)',
                    opacity: showControls ? 1 : 0, transition: 'opacity 0.3s ease',
                    display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
                    pointerEvents: showControls ? 'auto' : 'none', zIndex: 5
                }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        <h3 style={{ margin: 0, color: '#fff', textShadow: '0 1px 2px rgba(0,0,0,0.8)', fontSize: '1.1rem', fontWeight: '500' }}>{title}</h3>
                        {/* Hide buffered cache seconds for live streams — meaningless and confusing */}
                        {!isLiveStream && <span style={{ fontSize: '0.85rem', color: '#ccc' }}>Cache: {bufferedSeconds}s</span>}
                    </div>

                    {isFullscreen && (
                        <button
                            onClick={toggleFullscreen}
                            style={{
                                background: 'rgba(255,255,255,0.1)', border: 'none', color: '#fff',
                                borderRadius: '50%', width: '40px', height: '40px',
                                cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
                                fontSize: '1.2rem'
                            }}
                        >
                            ✕
                        </button>
                    )}
                </div>
            )}

            {/* Bottom Controls (Hidden for embeds) */}
            {type !== 'embed' && (
                <div style={{
                    position: 'absolute', bottom: 0, left: 0, right: 0,
                    padding: '1.5rem 2rem',
                    background: 'linear-gradient(to top, rgba(0,0,0,0.9) 10%, transparent 100%)',
                    opacity: showControls ? 1 : 0, transition: 'opacity 0.3s ease',
                    pointerEvents: showControls ? 'auto' : 'none',
                    display: 'flex', flexDirection: 'column', gap: '0.5rem', zIndex: 5
                }}>
                    {/* Seek Bar or LIVE indicator */}
                    {type !== 'embed' && (
                        isLiveStream ? (
                            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '0 4px' }}>
                                <div style={{
                                    display: 'flex', alignItems: 'center', gap: '8px',
                                    background: 'rgba(239,68,68,0.2)', border: '1px solid rgba(239,68,68,0.5)',
                                    borderRadius: '20px', padding: '4px 14px',
                                }}>
                                    <div style={{
                                        width: '8px', height: '8px', borderRadius: '50%',
                                        background: '#ef4444',
                                        animation: 'pulse-live 1.5s ease-in-out infinite',
                                    }} />
                                    <span style={{ fontSize: '0.8rem', fontWeight: '700', color: '#ef4444', letterSpacing: '1px' }}>LIVE</span>
                                </div>
                                <style>{`@keyframes pulse-live { 0%,100%{opacity:1} 50%{opacity:0.3} }`}</style>
                            </div>
                        ) : (
                            <div style={{
                                display: 'flex', alignItems: 'center', gap: '1rem',
                                position: 'relative', height: '24px'
                            }}>
                                <span style={{ fontSize: '0.9rem', color: '#ddd', minWidth: '45px', textAlign: 'right' }}>{formatTime(currentTime)}</span>

                                <div style={{ flex: 1, position: 'relative', height: '6px', cursor: 'pointer', display: 'flex', alignItems: 'center' }}>
                                    <div style={{
                                        position: 'absolute', left: 0, right: 0, height: '4px',
                                        background: 'rgba(255,255,255,0.2)', borderRadius: '2px'
                                    }} />

                                    <div style={{
                                        position: 'absolute', left: 0,
                                        width: `${buffered}%`, height: '4px',
                                        background: 'rgba(255,255,255,0.4)', borderRadius: '2px',
                                        transition: 'width 0.2s linear'
                                    }} />

                                    <input
                                        type="range"
                                        min="0"
                                        max="100"
                                        value={progress || 0}
                                        onChange={handleSeek}
                                        style={{
                                            width: '100%', height: '100%', margin: 0, padding: 0,
                                            opacity: 0, cursor: 'pointer', position: 'absolute', zIndex: 10
                                        }}
                                    />

                                    <div style={{
                                        position: 'absolute', left: 0,
                                        width: `${progress}%`, height: '4px',
                                        background: '#6366f1', borderRadius: '2px',
                                        pointerEvents: 'none'
                                    }} />

                                    <div style={{
                                        position: 'absolute', left: `${progress}%`,
                                        width: '12px', height: '12px',
                                        background: '#fff', borderRadius: '50%',
                                        transform: 'translate(-50%, 0)',
                                        pointerEvents: 'none',
                                        boxShadow: '0 0 4px rgba(0,0,0,0.5)'
                                    }} />
                                </div>

                                <span style={{ fontSize: '0.9rem', color: '#ddd', minWidth: '45px' }}>{formatTime(duration)}</span>
                            </div>
                        )
                    )}

                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0 0.5rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
                            {type !== 'embed' && (
                                <button
                                    onClick={togglePlay}
                                    style={{
                                        background: 'transparent', border: 'none', color: '#fff',
                                        cursor: 'pointer', fontSize: '2rem', padding: '0'
                                    }}
                                >
                                    {isPlaying ? '⏸' : '▶'}
                                </button>
                            )}

                            {showNext && (
                                <button
                                    onClick={(e) => { e.stopPropagation(); onNext(); }}
                                    title="Next Episode"
                                    style={{
                                        background: 'transparent', border: 'none', color: '#fff',
                                        cursor: 'pointer', fontSize: (type === 'embed' ? '1.5rem' : '2rem'), padding: '0',
                                        opacity: 0.9, marginLeft: (type === 'embed' ? '0' : '0.5rem')
                                    }}
                                >
                                    ⏭
                                </button>
                            )}

                            {type !== 'embed' && (
                                <div className="volume-control" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginLeft: '1rem' }}>
                                    <span style={{ fontSize: '1.2rem' }}>🔈</span>
                                    <input
                                        type="range" min="0" max="1" step="0.1" value={volume}
                                        onChange={(e) => { setVolume(e.target.value); videoRef.current.volume = e.target.value; }}
                                        style={{ width: '80px', accentColor: '#fff', height: '4px' }}
                                    />
                                </div>
                            )}
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', position: 'relative' }}>
                            {subtitles && subtitles.length > 0 && (
                                <div style={{ position: 'relative' }}>
                                    <button
                                        onClick={(e) => { e.stopPropagation(); setShowSubtitleMenu(!showSubtitleMenu); }}
                                        style={{
                                            background: 'transparent', border: 'none', color: subtitlesEnabled ? '#6366f1' : '#fff',
                                            cursor: 'pointer', fontSize: '1.4rem', padding: '0',
                                            opacity: subtitlesEnabled ? 1 : 0.7,
                                            display: 'flex', alignItems: 'center', justifyContent: 'center'
                                        }}
                                        title="Subtitles"
                                    >
                                        <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                                            <path d="M19 4H5c-1.11 0-2 .9-2 2v12c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V6c0-1.1-.89-2-2-2zm-8 7H9.5v-.5h-2v3h2V13H11v1c0 .55-.45 1-1 1H7c-.55 0-1-.45-1-1v-4c0-.55.45-1 1-1h3c.55 0 1 .45 1 1v1zm7 0h-1.5v-.5h-2v3h2V13H18v1c0 .55-.45 1-1 1h-3c-.55 0-1-.45-1-1v-4c0-.55.45-1 1-1h3c.55 0 1 .45 1 1v1z" />
                                        </svg>
                                    </button>

                                    {showSubtitleMenu && (
                                        <div style={{
                                            position: 'absolute', bottom: '150%', right: '0',
                                            background: 'rgba(20, 20, 25, 0.95)',
                                            backdropFilter: 'blur(10px)',
                                            border: '1px solid rgba(255,255,255,0.1)',
                                            borderRadius: '12px', padding: '8px',
                                            minWidth: '160px', zIndex: 100,
                                            boxShadow: '0 8px 32px rgba(0,0,0,0.5)'
                                        }}>
                                            <div style={{ padding: '8px', borderBottom: '1px solid rgba(255,255,255,0.05)', marginBottom: '4px', fontSize: '0.8rem', opacity: 0.6, fontWeight: 'bold' }}>SUBTITLES</div>

                                            <div style={{ padding: '0 8px 8px 8px' }}>
                                                <input
                                                    type="text"
                                                    placeholder="Search language..."
                                                    value={subtitleSearch}
                                                    onChange={(e) => setSubtitleSearch(e.target.value)}
                                                    onClick={(e) => e.stopPropagation()}
                                                    style={{
                                                        width: '100%',
                                                        background: 'rgba(255,255,255,0.05)',
                                                        border: '1px solid rgba(255,255,255,0.1)',
                                                        borderRadius: '6px',
                                                        padding: '6px 10px',
                                                        color: '#fff',
                                                        fontSize: '0.8rem',
                                                        outline: 'none'
                                                    }}
                                                />
                                            </div>

                                            <button
                                                onClick={() => { setSubtitlesEnabled(!subtitlesEnabled); setShowSubtitleMenu(false); }}
                                                style={{
                                                    width: '100%', padding: '8px 12px', textAlign: 'left',
                                                    background: 'transparent', border: 'none', color: 'white',
                                                    borderRadius: '6px', cursor: 'pointer', fontSize: '0.9rem',
                                                    display: 'flex', justifyContent: 'space-between', alignItems: 'center'
                                                }}
                                            >
                                                <span>{subtitlesEnabled ? 'Turn Off' : 'Turn On'}</span>
                                                <span style={{ fontSize: '0.7rem', opacity: 0.5 }}>{subtitlesEnabled ? 'ON' : 'OFF'}</span>
                                            </button>

                                            {subtitlesEnabled && (
                                                <div style={{
                                                    marginTop: '4px',
                                                    borderTop: '1px solid rgba(255,255,255,0.05)',
                                                    paddingTop: '4px',
                                                    maxHeight: '200px',
                                                    overflowY: 'auto',
                                                    scrollbarWidth: 'thin'
                                                }}>
                                                    {subtitles
                                                        .filter(sub => sub.lang.toLowerCase().includes(subtitleSearch.toLowerCase()))
                                                        .map((sub, idx) => {
                                                            // Calculate actual index in original subtitles array
                                                            const originalIdx = subtitles.findIndex(s => s === sub);
                                                            return (
                                                                <button
                                                                    key={originalIdx}
                                                                    onClick={() => {
                                                                        setPreferredLang(sub.lang);
                                                                        localStorage.setItem('preferred_subtitle_lang', sub.lang);
                                                                        setShowSubtitleMenu(false);
                                                                    }}
                                                                    style={{
                                                                        width: '100%', padding: '10px 12px', textAlign: 'left',
                                                                        background: preferredLang === sub.lang ? 'rgba(99, 102, 241, 0.2)' : 'transparent',
                                                                        border: 'none', color: preferredLang === sub.lang ? '#6366f1' : 'white',
                                                                        borderRadius: '8px', cursor: 'pointer', fontSize: '0.9rem',
                                                                        display: 'flex', alignItems: 'center', gap: '10px',
                                                                        transition: 'all 0.2s ease',
                                                                        marginBottom: '2px'
                                                                    }}
                                                                >
                                                                    <div style={{ width: '18px', display: 'flex', justifyContent: 'center' }}>
                                                                        {preferredLang === sub.lang ? '✓' : ''}
                                                                    </div>
                                                                    <span style={{ fontWeight: preferredLang === sub.lang ? 'bold' : 'normal' }}>{sub.lang}</span>
                                                                </button>
                                                            );

                                                        })}
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            )}

                            <button
                                onClick={toggleFullscreen}
                                style={{
                                    background: 'transparent', border: 'none', color: '#fff',
                                    cursor: 'pointer', fontSize: '1.8rem', padding: '0'
                                }}
                                title="Fullscreen"
                            >
                                ⛶
                            </button>
                        </div>
                    </div>
                </div>
            )}

            <style>{`
                @media (max-width: 768px) {
                    .volume-control { display: none !important; }
                }
                @keyframes spin { to { transform: rotate(360deg); } }
            `}</style>
        </div>
    );
};

export default VideoPlayer;