import React, { useRef, useEffect, useState } from 'react';

const VideoPlayer = ({ url, title, onClose, onNext, showNext, autoPlay = true }) => {
    const videoRef = useRef(null);
    const [isPlaying, setIsPlaying] = useState(autoPlay);
    const [isBuffering, setIsBuffering] = useState(true); // Start buffering initially
    const [progress, setProgress] = useState(0);
    const [buffered, setBuffered] = useState(0); // Buffered percentage
    const [bufferedSeconds, setBufferedSeconds] = useState(0); // Buffered seconds ahead
    const [volume, setVolume] = useState(1);
    const [showControls, setShowControls] = useState(true);
    const controlsTimeoutRef = useRef(null);
    const [isFullscreen, setIsFullscreen] = useState(false);
    const playerContainerRef = useRef(null);
    const [currentTime, setCurrentTime] = useState(0);
    const [duration, setDuration] = useState(0);

    useEffect(() => {
        const video = videoRef.current;
        if (!video) return;

        const updateProgress = () => {
            if (video.duration) {
                setCurrentTime(video.currentTime);
                setDuration(video.duration);
                setProgress((video.currentTime / video.duration) * 100);

                // Calculate buffer
                if (video.buffered.length > 0) {
                    // Find the buffered range that covers the current time
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
        video.addEventListener('progress', updateProgress); // Update buffer on download progress
        video.addEventListener('play', handlePlay);
        video.addEventListener('pause', handlePause);
        video.addEventListener('waiting', handleWaiting);
        video.addEventListener('canplay', handleCanPlay);
        video.addEventListener('playing', handlePlaying);
        video.addEventListener('ended', handleEnded);

        // Auto-play if requested
        if (autoPlay) {
            video.play().catch(e => console.log("Autoplay prevented:", e));
        }

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
    }, [autoPlay, showNext, onNext]);

    // Hiding controls on idle
    const resetControlsTimeout = () => {
        setShowControls(true);
        if (controlsTimeoutRef.current) clearTimeout(controlsTimeoutRef.current);
        controlsTimeoutRef.current = setTimeout(() => {
            if (isPlaying) setShowControls(false);
        }, 2500); // 2.5s delay
    };

    const handleMouseMove = () => resetControlsTimeout();
    const handleTouchStart = () => {
        // Toggle controls on touch if they are hidden, or keep them visible
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
        const seekTime = (e.target.value / 100) * videoRef.current.duration;
        videoRef.current.currentTime = seekTime;
        setProgress(e.target.value);
    };

    const toggleFullscreen = () => {
        if (!document.fullscreenElement) {
            if (playerContainerRef.current) {
                playerContainerRef.current.requestFullscreen().catch(err => {
                    console.error(`Error attempting to enable fullscreen: ${err.message}`);
                });
                setIsFullscreen(true);
            }
        } else {
            document.exitFullscreen();
            setIsFullscreen(false);
        }
    };

    // Format time (e.g., 90 -> 1:30)
    const formatTime = (seconds) => {
        const min = Math.floor(seconds / 60);
        const sec = Math.floor(seconds % 60);
        return `${min}:${sec < 10 ? '0' : ''}${sec}`;
    };

    return (
        <div
            ref={playerContainerRef}
            className="video-player-container"
            onMouseMove={handleMouseMove}
            onTouchStart={handleTouchStart}
            onMouseLeave={() => isPlaying && setShowControls(false)}
            style={{
                width: '100%',
                height: '100%',
                backgroundColor: '#000',
                position: 'relative',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                overflow: 'hidden',
                fontFamily: 'monospace' // MPV style font
            }}
        >
            <video
                ref={videoRef}
                src={url}
                style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                onClick={togglePlay}
                onDoubleClick={toggleFullscreen}
                playsInline
            />

            {/* Buffering Indicator */}
            {isBuffering && (
                <div style={{
                    position: 'absolute', inset: 0,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    background: 'rgba(0,0,0,0.1)', // Subtle overlay
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
            {!isPlaying && !isBuffering && (
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

            {/* Top Bar - Title & Close & Cache Info */}
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
                    {/* MPV Style Cache Text */}
                    <span style={{ fontSize: '0.85rem', color: '#ccc' }}>Cache: {bufferedSeconds}s</span>
                </div>

                {/* Close Button - Show if fullscreen or if requested by parent context via specific styling needs */}
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

            {/* Bottom Controls */}
            <div style={{
                position: 'absolute', bottom: 0, left: 0, right: 0,
                padding: '1.5rem 2rem',
                background: 'linear-gradient(to top, rgba(0,0,0,0.9) 10%, transparent 100%)',
                opacity: showControls ? 1 : 0, transition: 'opacity 0.3s ease',
                pointerEvents: showControls ? 'auto' : 'none',
                display: 'flex', flexDirection: 'column', gap: '0.5rem', zIndex: 5
            }}>
                {/* Seek Bar Container */}
                <div style={{
                    display: 'flex', alignItems: 'center', gap: '1rem',
                    position: 'relative', height: '24px'
                }}>
                    <span style={{ fontSize: '0.9rem', color: '#ddd', minWidth: '45px', textAlign: 'right' }}>{formatTime(currentTime)}</span>

                    {/* Progress Bar Wrapper */}
                    <div style={{ flex: 1, position: 'relative', height: '6px', cursor: 'pointer', display: 'flex', alignItems: 'center' }}>
                        {/* Background Track */}
                        <div style={{
                            position: 'absolute', left: 0, right: 0, height: '4px',
                            background: 'rgba(255,255,255,0.2)', borderRadius: '2px'
                        }} />

                        {/* Buffered Bar */}
                        <div style={{
                            position: 'absolute', left: 0,
                            width: `${buffered}%`, height: '4px',
                            background: 'rgba(255,255,255,0.4)', borderRadius: '2px',
                            transition: 'width 0.2s linear'
                        }} />

                        {/* Playhead Input - Invisible but functional */}
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

                        {/* Visual Playhead Bar */}
                        <div style={{
                            position: 'absolute', left: 0,
                            width: `${progress}%`, height: '4px',
                            background: '#6366f1', borderRadius: '2px',
                            pointerEvents: 'none'
                        }} />

                        {/* Visual Playhead Handle */}
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

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0 0.5rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
                        <button
                            onClick={togglePlay}
                            style={{
                                background: 'transparent', border: 'none', color: '#fff',
                                cursor: 'pointer', fontSize: '2rem', padding: '0'
                            }}
                        >
                            {isPlaying ? '⏸' : '▶'}
                        </button>

                        {/* Next Episode Button */}
                        {showNext && (
                            <button
                                onClick={(e) => { e.stopPropagation(); onNext(); }}
                                title="Next Episode"
                                style={{
                                    background: 'transparent', border: 'none', color: '#fff',
                                    cursor: 'pointer', fontSize: '2rem', padding: '0',
                                    opacity: 0.9, marginLeft: '0.5rem'
                                }}
                            >
                                ⏭
                            </button>
                        )}

                        <div className="volume-control" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginLeft: '1rem' }}>
                            <span style={{ fontSize: '1.2rem' }}>🔈</span>
                            <input
                                type="range" min="0" max="1" step="0.1" value={volume}
                                onChange={(e) => { setVolume(e.target.value); videoRef.current.volume = e.target.value; }}
                                style={{ width: '80px', accentColor: '#fff', height: '4px' }}
                            />
                        </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
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

            {/* Custom Styles for Mobile Responsiveness if needed */}
            <style>{`
                @media (max-width: 768px) {
                    .volume-control { display: none !important; } /* Hide volume on mobile to save space */
                }
                @keyframes spin { to { transform: rotate(360deg); } }
            `}</style>
        </div>
    );
};

export default VideoPlayer;
