import React, { useState, useEffect, useMemo } from 'react';

// ─── Famelack data source (plain JSON, same as Famelack uses internally) ─────
const FAMELACK_RAW = 'https://raw.githubusercontent.com/famelack/famelack-data/main/tv/raw';

// Parse a YouTube embed URL into a clean embed URL with autoplay
function cleanYoutubeEmbedUrl(url) {
    if (!url) return null;
    // Handle watch?v= format
    if (url.includes('youtube.com/watch?v=')) {
        const id = url.split('v=')[1]?.split('&')[0];
        url = `https://www.youtube.com/embed/${id}`;
    } else if (url.includes('youtu.be/')) {
        const id = url.split('youtu.be/')[1]?.split('?')[0];
        url = `https://www.youtube.com/embed/${id}`;
    }

    // Normalize: use youtube.com (not nocookie) for better compatibility
    let cleanUrl = url.replace('www.youtube-nocookie.com', 'www.youtube.com')
        .replace('youtube-nocookie.com', 'www.youtube.com');
    
    // Add autoplay if not already present
    const separator = cleanUrl.includes('?') ? '&' : '?';
    if (!cleanUrl.includes('autoplay=')) cleanUrl += `${separator}autoplay=1`;
    if (!cleanUrl.includes('mute=')) cleanUrl += '&mute=0';
    return cleanUrl;
}

// ─── Component ────────────────────────────────────────────────────────────────
const TVDiscovery = ({ onStream, API_BASE = '' }) => {
    const [viewMode, setViewMode] = useState('countries');
    const [allItems, setAllItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [selectedCountry, setSelectedCountry] = useState(null);
    const [searchQuery, setSearchQuery] = useState('');

    // --- Custom Channels State ---
    const DEFAULT_CHANNELS = [
        {
            id: 'default_iptv_org',
            title: 'Free World IPTV Playlist',
            poster_url: '',
            url: 'https://iptv-org.github.io/iptv/index.m3u',
            stream_type: 'm3u_playlist',
            source: 'tv',
            type: 'channel',
            is_user_added: true
        }
    ];

    const [userChannels, setUserChannels] = useState(() => {
        const saved = localStorage.getItem('genga_user_tv_channels');
        if (saved) {
            try {
                const parsed = JSON.parse(saved);
                if (Array.isArray(parsed) && parsed.length > 0) return parsed;
            } catch (e) {}
        }
        return DEFAULT_CHANNELS;
    });
    const [showAddForm, setShowAddForm] = useState(false);
    const [newChanName, setNewChanName] = useState('');
    const [newChanUrl, setNewChanUrl] = useState('');

    // Persist user channels
    useEffect(() => {
        localStorage.setItem('genga_user_tv_channels', JSON.stringify(userChannels));
    }, [userChannels]);

    useEffect(() => {
        setSearchQuery('');
        setAllItems([]);
        setError(null);
        if (viewMode === 'countries') fetchCountries();
        else if (viewMode === 'channels' && selectedCountry) {
            if (selectedCountry.id === 'user_custom') {
                setAllItems(userChannels);
                setLoading(false);
            } else {
                fetchChannels(selectedCountry.id);
            }
        }
    }, [viewMode, selectedCountry, userChannels]);

    const fetchCountries = async () => {
        setLoading(true);
        try {
            const res = await fetch(`${API_BASE}/api/tv/countries`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            
            // Add "My Channels" as a virtual country if there are user channels
            const countries = data.results || [];
            const finalCountries = [
                { id: 'user_custom', title: '⭐ My Custom Channels', type: 'country' },
                ...countries
            ];
            setAllItems(finalCountries);
        } catch (e) {
            setError(`Could not load countries: ${e.message}`);
        } finally {
            setLoading(false);
        }
    };

    const fetchChannels = async (code) => {
        setLoading(true);
        try {
            const res = await fetch(`${API_BASE}/api/tv/country/${code}`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            setAllItems(data.results || []);
        } catch (e) {
            setError(`Could not load channels: ${e.message}`);
        } finally {
            setLoading(false);
        }
    };

    const items = useMemo(() => {
        if (!searchQuery.trim()) return allItems;
        const q = searchQuery.toLowerCase();
        return allItems.filter(item =>
            item.title?.toLowerCase().includes(q) ||
            item.name?.toLowerCase().includes(q)
        );
    }, [allItems, searchQuery]);

    const handleItemClick = (item) => {
        if (item.type === 'country') {
            setSelectedCountry(item);
            setViewMode('channels');
        } else {
            if (onStream) onStream(item);
        }
    };

    const handleAddChannel = (e) => {
        e.preventDefault();
        if (!newChanName || !newChanUrl) return;

        let streamType = 'hls';
        let finalUrl = newChanUrl;

        if (newChanUrl.includes('youtube.com') || newChanUrl.includes('youtu.be')) {
            streamType = 'embed';
            finalUrl = cleanYoutubeEmbedUrl(newChanUrl);
        } else if (newChanUrl.toLowerCase().endsWith('.m3u') || (newChanUrl.toLowerCase().includes('.m3u') && !newChanUrl.toLowerCase().includes('.m3u8'))) {
            streamType = 'm3u_playlist';
        } else if (newChanUrl.toLowerCase().endsWith('.m3u8') || newChanUrl.toLowerCase().includes('.m3u8?')) {
            streamType = 'hls';
        }

        const newChannel = {
            id: `user_${Date.now()}`,
            title: newChanName,
            poster_url: '',
            url: finalUrl,
            stream_type: streamType,
            source: 'tv',
            type: 'channel',
            is_user_added: true
        };

        setUserChannels(prev => [...prev, newChannel]);
        setNewChanName('');
        setNewChanUrl('');
        setShowAddForm(false);
    };

    const removeChannel = (id) => {
        setUserChannels(prev => prev.filter(c => c.id !== id));
    };

    const highlightMatch = (text, query) => {
        if (!query) return text;
        const idx = text.toLowerCase().indexOf(query.toLowerCase());
        if (idx === -1) return text;
        return (
            <>{text.substring(0, idx)}<span style={highlightStyle}>{text.substring(idx, idx + query.length)}</span>{text.substring(idx + query.length)}</>
        );
    };

    // ── Components ─────────────────────────────────────────────────────────────
    const CountryCard = ({ item }) => {
        const parts = item.title.split(' ');
        const flag = item.id === 'user_custom' ? '⭐' : parts[0];
        const name = item.id === 'user_custom' ? item.title : (parts.slice(1).join(' ') || item.title);
        return (
            <div onClick={() => handleItemClick(item)} style={cardStyle} onMouseEnter={hoverOn} onMouseLeave={hoverOff}>
                <span style={{ fontSize: '2.4rem', lineHeight: 1 }}>{flag}</span>
                <span style={nameStyle}>{highlightMatch(name, searchQuery)}</span>
            </div>
        );
    };

    const ChannelCard = ({ item }) => {
        const [imgError, setImgError] = useState(false);
        return (
            <div style={{ position: 'relative' }} onMouseEnter={hoverOn} onMouseLeave={hoverOff}>
                <div onClick={() => handleItemClick(item)} style={{ ...cardStyle, minHeight: '140px', justifyContent: 'center' }}>
                    <div style={{ width: 64, height: 64, flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        {item.poster_url && !imgError ? (
                            <img src={item.poster_url} alt={item.title} onError={() => setImgError(true)}
                                style={{ width: 64, height: 64, objectFit: 'contain', borderRadius: 8 }} />
                        ) : (
                            <div style={{ width: 64, height: 64, background: 'linear-gradient(135deg,#6366f1,#8b5cf6)', borderRadius: 12, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.5rem', fontWeight: 700, color: '#fff' }}>
                                {item.title.charAt(0).toUpperCase()}
                            </div>
                        )}
                    </div>
                    <span style={{ ...nameStyle, fontSize: '0.8rem', textAlign: 'center', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                        {highlightMatch(item.title, searchQuery)}
                    </span>
                    <span style={{
                        fontSize: '0.65rem', padding: '2px 8px', borderRadius: 10,
                        background: (item.stream_type === 'embed' || item.stream_type === 'youtube_hls')
                            ? 'rgba(255,0,0,0.15)' : 'rgba(34,197,94,0.15)',
                        color: (item.stream_type === 'embed' || item.stream_type === 'youtube_hls')
                            ? '#f87171' : '#22c55e',
                        border: `1px solid ${(item.stream_type === 'embed' || item.stream_type === 'youtube_hls')
                            ? 'rgba(255,0,0,0.3)' : 'rgba(34,197,94,0.3)'}`,
                        fontWeight: 700, letterSpacing: '0.5px', textTransform: 'uppercase',
                    }}>{(item.stream_type === 'embed' || item.stream_type === 'youtube_hls') ? '▶ YouTube' : '🔴 Live'}</span>
                </div>
                {item.is_user_added && (
                    <button 
                        onClick={(e) => { e.stopPropagation(); removeChannel(item.id); }}
                        style={deleteBtnStyle}
                    >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                    </button>
                )}
            </div>
        );
    };

    // ── Render ────────────────────────────────────────────────────────────────
    return (
        <div style={{ padding: '20px 40px', minHeight: '100%' }}>
            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: 20, gap: 16, flexWrap: 'wrap' }}>
                {viewMode === 'channels' && (
                    <button onClick={() => { setViewMode('countries'); setSelectedCountry(null); }} style={backBtnStyle}>
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="15 18 9 12 15 6" /></svg>
                        Back
                    </button>
                )}
                <div style={{ flex: 1 }}>
                    <h2 style={headingStyle}>{viewMode === 'countries' ? '📺 Live TV' : selectedCountry?.title}</h2>
                </div>
                <button onClick={() => setShowAddForm(!showAddForm)} style={addMainBtnStyle}>
                    {showAddForm ? 'Close' : '+ Add Channel'}
                </button>
            </div>

            {/* Add Channel Form */}
            {showAddForm && (
                <form onSubmit={handleAddChannel} style={formStyle}>
                    <input 
                        type="text" placeholder="Channel Name (e.g. My Sports HD)" 
                        value={newChanName} onChange={e => setNewChanName(e.target.value)}
                        style={inputStyle} required
                    />
                    <input 
                        type="text" placeholder="IPTV .m3u8 URL or YouTube Live URL" 
                        value={newChanUrl} onChange={e => setNewChanUrl(e.target.value)}
                        style={inputStyle} required
                    />
                    <button type="submit" style={submitBtnStyle}>Save Channel</button>
                </form>
            )}

            {/* Search bar */}
            {!loading && allItems.length > 0 && (
                <div style={{ marginBottom: 24, position: 'relative', maxWidth: 480 }}>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.4)" strokeWidth="2"
                        style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none' }}>
                        <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
                    </svg>
                    <input
                        type="text" value={searchQuery}
                        onChange={e => setSearchQuery(e.target.value)}
                        placeholder="Search channels or countries…"
                        style={searchStyle}
                    />
                </div>
            )}

            {/* Content */}
            {loading ? (
                <div style={statusContainerStyle}>
                    <div style={spinnerStyle} />
                    <span>Loading...</span>
                </div>
            ) : error ? (
                <div style={statusContainerStyle}>
                    <div style={{ fontSize: '2rem', marginBottom: 12 }}>⚠️</div>
                    <p>{error}</p>
                    <button onClick={() => viewMode === 'countries' ? fetchCountries() : fetchChannels(selectedCountry?.id)} style={retryBtnStyle}>Retry</button>
                </div>
            ) : items.length === 0 ? (
                <div style={statusContainerStyle}>
                    <div style={{ fontSize: '3rem', marginBottom: 16 }}>🔍</div>
                    <p>{searchQuery ? `No results for "${searchQuery}"` : 'No channels found.'}</p>
                </div>
            ) : (
                <div style={{ display: 'grid', gridTemplateColumns: viewMode === 'countries' ? 'repeat(auto-fill,minmax(150px,1fr))' : 'repeat(auto-fill,minmax(160px,1fr))', gap: 16 }}>
                    {items.map(item => viewMode === 'countries'
                        ? <CountryCard key={item.id} item={item} />
                        : <ChannelCard key={item.id} item={item} />
                    )}
                </div>
            )}
        </div>
    );
};

// ─── Styles ───────────────────────────────────────────────────────────────────
const cardStyle = {
    background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)',
    borderRadius: 16, padding: '20px 16px', cursor: 'pointer', textAlign: 'center',
    transition: 'all 0.2s ease', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10,
};
const hoverOn = e => {
    e.currentTarget.style.background = 'rgba(99,102,241,0.15)';
    e.currentTarget.style.borderColor = 'rgba(99,102,241,0.4)';
    e.currentTarget.style.transform = 'translateY(-4px)';
};
const hoverOff = e => {
    e.currentTarget.style.background = 'rgba(255,255,255,0.04)';
    e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)';
    e.currentTarget.style.transform = 'translateY(0)';
};
const nameStyle = {
    fontSize: '0.85rem', fontWeight: 600, color: 'rgba(255,255,255,0.9)',
    lineHeight: 1.3, maxWidth: '100%', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
};
const highlightStyle = { color: '#6366f1', fontWeight: 800 };
const backBtnStyle = {
    background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.15)',
    color: 'white', padding: '8px 16px', borderRadius: 10, cursor: 'pointer',
    display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.9rem', fontWeight: 500,
};
const headingStyle = {
    fontSize: '1.8rem', fontWeight: 700, margin: 0,
    background: 'linear-gradient(90deg,#fff,#a8b2d1)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
};
const searchStyle = {
    width: '100%', padding: '12px 42px', background: 'rgba(255,255,255,0.06)',
    border: '1px solid rgba(255,255,255,0.12)', borderRadius: 12, color: 'white',
    fontSize: '0.95rem', boxSizing: 'border-box',
};
const addMainBtnStyle = {
    background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.3)',
    color: '#a5b4fc', padding: '8px 20px', borderRadius: 12, cursor: 'pointer',
    fontWeight: 600, fontSize: '0.85rem', transition: 'all 0.2s',
};
const formStyle = {
    background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)',
    borderRadius: 16, padding: 20, marginBottom: 24, display: 'flex', gap: 12, flexWrap: 'wrap'
};
const inputStyle = {
    flex: 1, minWidth: '200px', padding: '12px 16px', background: 'rgba(0,0,0,0.2)',
    border: '1px solid rgba(255,255,255,0.1)', borderRadius: 10, color: 'white', outline: 'none'
};
const submitBtnStyle = {
    background: '#6366f1', color: 'white', border: 'none', padding: '12px 24px',
    borderRadius: 10, fontWeight: 600, cursor: 'pointer'
};
const deleteBtnStyle = {
    position: 'absolute', top: 8, right: 8, background: 'rgba(239,68,68,0.2)',
    border: '1px solid rgba(239,68,68,0.4)', color: '#f87171', width: 28, height: 28,
    borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
    cursor: 'pointer', transition: 'all 0.2s', zIndex: 10
};
const statusContainerStyle = { display: 'flex', flexDirection: 'column', alignItems: 'center', padding: 80, gap: 16, color: 'rgba(255,255,255,0.4)' };
const spinnerStyle = { width: 40, height: 40, border: '3px solid rgba(255,255,255,0.1)', borderTopColor: '#6366f1', borderRadius: '50%', animation: 'spin 1s linear infinite' };
const retryBtnStyle = { marginTop: 12, padding: '8px 20px', background: 'rgba(99,102,241,0.2)', border: '1px solid rgba(99,102,241,0.4)', color: '#a5b4fc', borderRadius: 8, cursor: 'pointer' };

export default TVDiscovery;
