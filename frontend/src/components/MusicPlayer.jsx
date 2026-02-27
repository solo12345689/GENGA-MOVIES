import React, { useRef, useEffect, useState } from 'react';

const MusicPlayer = ({ track, onClose }) => {
    const audioRef = useRef(null);
    const [isPlaying, setIsPlaying] = useState(true);
    const [currentTime, setCurrentTime] = useState(0);
    const [duration, setDuration] = useState(0);
    const [volume, setVolume] = useState(1);
    const [progress, setProgress] = useState(0);

    useEffect(() => {
        const audio = audioRef.current;
        if (!audio || !track.stream_url) return;

        let hls = null;
        const setupSource = () => {
            const url = track.stream_url;
            if (url.includes('.m3u8')) {
                if (audio.canPlayType('application/vnd.apple.mpegurl')) {
                    audio.src = url;
                } else if (window.Hls) {
                    hls = new window.Hls();
                    hls.loadSource(url);
                    hls.attachMedia(audio);
                } else {
                    const script = document.createElement('script');
                    script.src = "https://cdn.jsdelivr.net/npm/hls.js@latest";
                    script.onload = () => {
                        if (window.Hls.isSupported()) {
                            hls = new window.Hls();
                            hls.loadSource(url);
                            hls.attachMedia(audio);
                        } else {
                            audio.src = url;
                        }
                    };
                    document.head.appendChild(script);
                }
            } else {
                audio.src = url;
            }
            audio.play().catch(e => console.log("Playback failed:", e));
        };

        setupSource();

        return () => {
            if (hls) hls.destroy();
            audio.src = '';
        };
    }, [track.stream_url]);

    const handleTimeUpdate = () => {
        if (audioRef.current) {
            setCurrentTime(audioRef.current.currentTime);
            setDuration(audioRef.current.duration);
            setProgress((audioRef.current.currentTime / audioRef.current.duration) * 100);
        }
    };

    const togglePlay = () => {
        if (audioRef.current.paused) {
            audioRef.current.play();
            setIsPlaying(true);
        } else {
            audioRef.current.pause();
            setIsPlaying(false);
        }
    };

    const handleSeek = (e) => {
        const seekTime = (e.target.value / 100) * audioRef.current.duration;
        audioRef.current.currentTime = seekTime;
        setProgress(e.target.value);
    };

    const formatTime = (seconds) => {
        const min = Math.floor(seconds / 60);
        const sec = Math.floor(seconds % 60);
        return `${min}:${sec < 10 ? '0' : ''}${sec}`;
    };

    return (
        <div
            className="music-player-bar"
            style={{
                position: 'fixed',
                bottom: 0,
                left: 0,
                right: 0,
                background: 'rgba(15, 15, 15, 0.85)',
                backdropFilter: 'blur(25px)',
                borderTop: '1px solid rgba(255, 255, 255, 0.1)',
                padding: '12px 24px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                zIndex: 1000,
                color: '#fff',
                boxShadow: '0 -10px 30px rgba(0,0,0,0.5)',
                height: '90px'
            }}
        >
            <audio
                ref={audioRef}
                onTimeUpdate={handleTimeUpdate}
                onPlay={() => setIsPlaying(true)}
                onPause={() => setIsPlaying(false)}
            />

            {/* Track Info */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px', width: '30%' }}>
                <img
                    src={track.poster_url}
                    alt={track.title}
                    style={{
                        width: '56px',
                        height: '56px',
                        borderRadius: '8px',
                        objectFit: 'cover',
                        boxShadow: '0 4px 12px rgba(0,0,0,0.3)'
                    }}
                />
                <div style={{ overflow: 'hidden' }}>
                    <h4 style={{ margin: 0, fontSize: '0.95rem', fontWeight: '600', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{track.title}</h4>
                    <p style={{ margin: 0, fontSize: '0.8rem', color: 'rgba(255,255,255,0.6)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{track.artists}</p>
                </div>
            </div>

            {/* Controls */}
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px', width: '40%' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
                    <button style={{ background: 'transparent', border: 'none', color: '#fff', fontSize: '1.2rem', cursor: 'pointer', opacity: 0.7 }}>⏮</button>
                    <button
                        onClick={togglePlay}
                        style={{
                            background: '#fff',
                            color: '#000',
                            border: 'none',
                            width: '40px',
                            height: '40px',
                            borderRadius: '50%',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: '1.2rem',
                            cursor: 'pointer',
                            transition: 'transform 0.2s'
                        }}
                        onMouseEnter={e => e.currentTarget.style.transform = 'scale(1.1)'}
                        onMouseLeave={e => e.currentTarget.style.transform = 'scale(1)'}
                    >
                        {isPlaying ? '⏸' : '▶'}
                    </button>
                    <button style={{ background: 'transparent', border: 'none', color: '#fff', fontSize: '1.2rem', cursor: 'pointer', opacity: 0.7 }}>⏭</button>
                </div>

                <div style={{ width: '100%', display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <span style={{ fontSize: '0.75rem', opacity: 0.6, minWidth: '35px', textAlign: 'right' }}>{formatTime(currentTime)}</span>
                    <div style={{ flex: 1, position: 'relative', height: '4px', background: 'rgba(255,255,255,0.1)', borderRadius: '2px' }}>
                        <div style={{ position: 'absolute', inset: 0, width: `${progress}%`, background: 'var(--primary)', borderRadius: '2px' }} />
                        <input
                            type="range"
                            min="0"
                            max="100"
                            value={progress || 0}
                            onChange={handleSeek}
                            style={{
                                position: 'absolute',
                                inset: 0,
                                width: '100%',
                                opacity: 0,
                                cursor: 'pointer',
                                height: '100%'
                            }}
                        />
                    </div>
                    <span style={{ fontSize: '0.75rem', opacity: 0.6, minWidth: '35px' }}>{formatTime(duration)}</span>
                </div>
            </div>

            {/* Volume & Close */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '20px', width: '30%', justifyContent: 'flex-end' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ opacity: 0.6 }}>🔈</span>
                    <input
                        type="range"
                        min="0"
                        max="1"
                        step="0.01"
                        value={volume}
                        onChange={e => {
                            const v = e.target.value;
                            setVolume(v);
                            audioRef.current.volume = v;
                        }}
                        style={{ width: '80px', height: '4px', accentColor: '#fff' }}
                    />
                </div>
                <button
                    onClick={onClose}
                    style={{ background: 'transparent', border: 'none', color: '#fff', fontSize: '1.2rem', cursor: 'pointer', opacity: 0.5 }}
                    onMouseEnter={e => e.currentTarget.style.opacity = 1}
                    onMouseLeave={e => e.currentTarget.style.opacity = 0.5}
                >
                    ✕
                </button>
            </div>
        </div>
    );
};

export default MusicPlayer;
