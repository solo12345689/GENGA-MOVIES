import React, { useState, useEffect, useMemo } from 'react';

// ─── Famelack data source (plain JSON, same as Famelack uses internally) ─────
const FAMELACK_RAW = 'https://raw.githubusercontent.com/famelack/famelack-data/c28d90693a3cf7466f1be73a290e209076b5b23f/channels/compressed';

// Parse a YouTube embed URL into a clean embed URL with autoplay
function cleanYoutubeEmbedUrl(url) {
    if (!url) return null;
    // Normalize: use youtube.com (not nocookie) for better compatibility
    let cleanUrl = url.replace('www.youtube-nocookie.com', 'www.youtube.com')
        .replace('youtube-nocookie.com', 'www.youtube.com');
    // Add autoplay if not already present
    const separator = cleanUrl.includes('?') ? '&' : '?';
    if (!cleanUrl.includes('autoplay=')) cleanUrl += `${separator}autoplay=1`;
    if (!cleanUrl.includes('mute=')) cleanUrl += '&mute=0';
    return cleanUrl;
}

// Parse a Famelack channel object into our standard format
function formatChannel(c) {
    const name = c.name || 'Unknown Channel';

    // User requested to remove NDTV channels (specifically NDTV Profit)
    if (name.toLowerCase().includes('ndtv profit')) return null;

    const iptv = (c.iptv_urls || []).filter(u => u && u.trim());
    const yt = (c.youtube_urls || []).filter(u => u && u.trim());

    let url, streamType;

    if (iptv.length > 0) {
        // Direct HLS/M3U8 stream — played via HLS.js
        url = iptv[0];
        streamType = 'hls';
    } else if (yt.length > 0) {
        // YouTube embed — played in iframe (same as Famelack.com)
        const embedUrl = cleanYoutubeEmbedUrl(yt[0]);
        if (!embedUrl) return null;
        url = embedUrl;
        streamType = 'embed';
    } else {
        return null; // No valid stream
    }

    return {
        id: c.nanoid || name.replace(/\s+/g, '_').toLowerCase(),
        title: name,
        poster_url: c.logo || '',
        url,
        stream_type: streamType,
        language: c.language || '',
        country: c.country || '',
        is_geo_blocked: c.isGeoBlocked || false,
        source: 'tv',
        type: 'channel',
    };
}

// ─── Component ────────────────────────────────────────────────────────────────
const TVDiscovery = ({ onStream }) => {
    const [viewMode, setViewMode] = useState('countries');
    const [allItems, setAllItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [selectedCountry, setSelectedCountry] = useState(null);
    const [searchQuery, setSearchQuery] = useState('');

    useEffect(() => {
        setSearchQuery('');
        setAllItems([]);
        setError(null);
        if (viewMode === 'countries') fetchCountries();
        else if (viewMode === 'channels' && selectedCountry) fetchChannels(selectedCountry.id);
    }, [viewMode, selectedCountry]);

    const fetchCountries = async () => {
        setLoading(true);
        try {
            // Use compressed metadata (same URL Famelack preloads)
            const res = await fetch(`${FAMELACK_RAW}/countries_metadata.json`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();

            const countries = Object.entries(data)
                .filter(([, info]) => info && info.hasChannels)
                .map(([code, info]) => {
                    const flag = code.length === 2
                        ? [...code.toUpperCase()].map(c => String.fromCodePoint(0x1F1E6 + c.charCodeAt(0) - 65)).join('')
                        : '';
                    return {
                        id: code.toLowerCase(),
                        title: `${flag} ${info.country || code}`,
                        name: info.country || code,
                        type: 'country',
                        source: 'tv',
                    };
                })
                .sort((a, b) => a.name.localeCompare(b.name));

            setAllItems(countries);
        } catch (e) {
            setError(`Could not load countries: ${e.message}`);
        } finally {
            setLoading(false);
        }
    };

    const fetchChannels = async (code) => {
        setLoading(true);
        try {
            const res = await fetch(`${FAMELACK_RAW}/countries/${code}.json`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const raw = await res.json();
            const channels = raw.map(formatChannel).filter(Boolean);
            setAllItems(channels);
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

    const highlightMatch = (text, query) => {
        if (!query) return text;
        const idx = text.toLowerCase().indexOf(query.toLowerCase());
        if (idx === -1) return text;
        return (
            <>{text.substring(0, idx)}<span style={highlightStyle}>{text.substring(idx, idx + query.length)}</span>{text.substring(idx + query.length)}</>
        );
    };

    // ── Country card ─────────────────────────────────────────────────────────
    const CountryCard = ({ item }) => {
        const parts = item.title.split(' ');
        const flag = parts[0];
        const name = parts.slice(1).join(' ') || item.title;
        return (
            <div onClick={() => handleItemClick(item)} style={cardStyle} onMouseEnter={hoverOn} onMouseLeave={hoverOff}>
                <span style={{ fontSize: '2.4rem', lineHeight: 1 }}>{flag}</span>
                <span style={nameStyle}>{highlightMatch(name, searchQuery)}</span>
            </div>
        );
    };

    // ── Channel card ─────────────────────────────────────────────────────────
    const ChannelCard = ({ item }) => {
        const [imgError, setImgError] = useState(false);
        return (
            <div onClick={() => handleItemClick(item)} style={{ ...cardStyle, minHeight: '140px', justifyContent: 'center' }} onMouseEnter={hoverOn} onMouseLeave={hoverOff}>
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
                    background: item.stream_type === 'embed'
                        ? 'rgba(255,0,0,0.15)' : 'rgba(34,197,94,0.15)',
                    color: item.stream_type === 'embed' ? '#f87171' : '#22c55e',
                    border: `1px solid ${item.stream_type === 'embed' ? 'rgba(255,0,0,0.3)' : 'rgba(34,197,94,0.3)'}`,
                    fontWeight: 700, letterSpacing: '0.5px', textTransform: 'uppercase',
                }}>{item.stream_type === 'embed' ? '▶ YouTube' : '🔴 Live'}</span>
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
                        Countries
                    </button>
                )}
                <div style={{ flex: 1 }}>
                    <h2 style={headingStyle}>{viewMode === 'countries' ? '📺 Live TV' : `${selectedCountry?.title} Channels`}</h2>
                    {!loading && allItems.length > 0 && (
                        <p style={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.85rem', margin: '4px 0 0' }}>
                            {items.length} / {allItems.length} {viewMode === 'countries' ? 'countries' : 'channels'}
                            {searchQuery && ` matching "${searchQuery}"`}
                        </p>
                    )}
                </div>
            </div>

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
                        placeholder={viewMode === 'countries' ? 'Search countries… e.g. India, Indo' : 'Search channels…'}
                        style={searchStyle}
                        onFocus={e => e.target.style.borderColor = 'rgba(99,102,241,0.6)'}
                        onBlur={e => e.target.style.borderColor = 'rgba(255,255,255,0.12)'}
                    />
                    {searchQuery && <button onClick={() => setSearchQuery('')} style={clearBtnStyle}>×</button>}
                </div>
            )}

            {/* Content */}
            {loading ? (
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: 80, gap: 16, color: 'rgba(255,255,255,0.4)' }}>
                    <div style={{ width: 40, height: 40, border: '3px solid rgba(255,255,255,0.1)', borderTopColor: '#6366f1', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
                    <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
                    <span>Loading {viewMode}…</span>
                </div>
            ) : error ? (
                <div style={{ textAlign: 'center', color: '#ef4444', padding: 80 }}>
                    <div style={{ fontSize: '2rem', marginBottom: 12 }}>⚠️</div>
                    <p>{error}</p>
                    <button onClick={() => viewMode === 'countries' ? fetchCountries() : fetchChannels(selectedCountry?.id)}
                        style={{ marginTop: 12, padding: '8px 20px', background: 'rgba(99,102,241,0.2)', border: '1px solid rgba(99,102,241,0.4)', color: '#a5b4fc', borderRadius: 8, cursor: 'pointer' }}>
                        Retry
                    </button>
                </div>
            ) : items.length === 0 ? (
                <div style={{ textAlign: 'center', color: 'rgba(255,255,255,0.4)', padding: 60 }}>
                    <div style={{ fontSize: '3rem', marginBottom: 16 }}>🔍</div>
                    <p style={{ fontSize: '1.1rem', fontWeight: 600 }}>{searchQuery ? `No results for "${searchQuery}"` : 'No channels found.'}</p>
                    {searchQuery && <button onClick={() => setSearchQuery('')} style={{ marginTop: 12, padding: '8px 20px', background: 'rgba(99,102,241,0.2)', border: '1px solid rgba(99,102,241,0.4)', color: '#a5b4fc', borderRadius: 8, cursor: 'pointer' }}>Clear</button>}
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

// ─── Shared styles ────────────────────────────────────────────────────────────
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
    display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.9rem', fontWeight: 500, flexShrink: 0,
};
const headingStyle = {
    fontSize: '1.8rem', fontWeight: 700, margin: 0,
    background: 'linear-gradient(90deg,#fff,#a8b2d1)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
};
const searchStyle = {
    width: '100%', padding: '12px 42px', background: 'rgba(255,255,255,0.06)',
    border: '1px solid rgba(255,255,255,0.12)', borderRadius: 12, color: 'white',
    fontSize: '0.95rem', outline: 'none', transition: 'border-color 0.2s', boxSizing: 'border-box',
};
const clearBtnStyle = {
    position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)',
    background: 'transparent', border: 'none', color: 'rgba(255,255,255,0.5)',
    cursor: 'pointer', fontSize: '1.1rem', lineHeight: 1, padding: 2,
};

export default TVDiscovery;
