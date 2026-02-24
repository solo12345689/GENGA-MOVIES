import React, { useState, useEffect } from 'react';

const MangaReader = ({ item, chapterId, chapterTitle, onBack, API_BASE }) => {
    const [pages, setPages] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchPages = async () => {
            setLoading(true);
            setError(null);
            try {
                const res = await fetch(`${API_BASE}/api/manga/read/${chapterId}`);
                if (!res.ok) throw new Error("Failed to fetch pages");
                const data = await res.json();
                setPages(data.pages || []);
            } catch (err) {
                console.error(err);
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };
        fetchPages();
    }, [chapterId, API_BASE]);

    return (
        <div style={{
            position: 'fixed',
            inset: 0,
            background: '#0a0a0f',
            zIndex: 300,
            display: 'flex',
            flexDirection: 'column',
            color: 'white',
            fontFamily: "'Inter', sans-serif"
        }}>
            {/* Header */}
            <div style={{
                height: '60px',
                padding: '0 1rem',
                borderBottom: '1px solid rgba(255,255,255,0.1)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                background: 'rgba(10,10,15,0.95)',
                zIndex: 30
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', overflow: 'hidden', flex: 1 }}>
                    <button onClick={onBack} style={{ background: 'rgba(255,255,255,0.1)', border: 'none', color: 'white', padding: '0.5rem 1rem', borderRadius: '20px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.9rem' }}>
                        <span>←</span> Back
                    </button>
                    <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                        <span style={{ fontWeight: '600', fontSize: '0.95rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{item.title}</span>
                        <span style={{ fontSize: '0.75rem', opacity: 0.5 }}>{chapterTitle}</span>
                    </div>
                </div>
                <div style={{ display: 'flex', gap: '10px' }}>
                    {/* UI Cleanup: Removed Paginated View and PDF buttons as requested */}
                </div>
            </div>

            {/* Content */}
            <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', alignItems: 'center', background: '#000' }}>
                {loading && (
                    <div style={{ marginTop: '100px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '20px' }}>
                        <div style={{ width: '40px', height: '40px', border: '3px solid rgba(255,255,255,0.1)', borderTopColor: '#6366f1', borderRadius: '50%', animation: 'spin 1s linear infinite' }}></div>
                        <span>Loading Pages...</span>
                    </div>
                )}

                {error && (
                    <div style={{ marginTop: '100px', color: '#ef4444' }}>
                        Error: {error}
                    </div>
                )}

                {!loading && !error && (
                    <div style={{ width: '100%', maxWidth: '800px' }}>
                        {pages.map((p, i) => (
                            <img
                                key={i}
                                src={`${API_BASE}/api/manga/image-proxy?url=${encodeURIComponent(p.img || p)}`}
                                alt={`Page ${i + 1}`}
                                style={{ width: '100%', display: 'block', height: 'auto' }}
                                loading="lazy"
                            />
                        ))}
                    </div>
                )}
            </div>

            <style>{`
                @keyframes spin { to { transform: rotate(360deg); } }
            `}</style>
        </div>
    );
};

export default MangaReader;
