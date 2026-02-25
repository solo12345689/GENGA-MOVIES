import React, { useState, useEffect } from 'react';

const MangaReader = ({ item, chapterId, chapterTitle, onBack, API_BASE }) => {
    const [localChapterId, setLocalChapterId] = useState(chapterId);
    const [localChapterTitle, setLocalChapterTitle] = useState(chapterTitle);
    const [pages, setPages] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const contentRef = React.useRef(null);

    // Extract all chapters in order
    const allChapters = item.volumes ? Object.values(item.volumes).flat() : [];
    const currentIndex = allChapters.findIndex(c => String(c.id) === String(localChapterId));

    // List is descending (Newest at index 0)
    // Next (Newer) is index - 1
    // Previous (Older) is index + 1
    const nextChapter = currentIndex > 0 ? allChapters[currentIndex - 1] : null;
    const prevChapter = currentIndex < allChapters.length - 1 ? allChapters[currentIndex + 1] : null;

    useEffect(() => {
        const fetchPages = async () => {
            setLoading(true);
            setError(null);
            try {
                const res = await fetch(`${API_BASE}/api/manga/read/${localChapterId}`);
                if (!res.ok) throw new Error("Failed to fetch pages");
                const data = await res.json();

                const fetchedPages = data.pages || [];
                setPages(fetchedPages);

                if (fetchedPages.length === 0) {
                    setError("No pages found for this chapter.");
                }

                // Scroll to top
                if (contentRef.current) contentRef.current.scrollTop = 0;
            } catch (err) {
                console.error(err);
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };
        fetchPages();
    }, [localChapterId, API_BASE]);

    const handleChapterSwitch = (chap) => {
        if (!chap) return;
        setLocalChapterId(chap.id);
        setLocalChapterTitle(chap.title);
    };

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
                        <span style={{ fontSize: '0.75rem', opacity: 0.5 }}>{localChapterTitle}</span>
                    </div>
                </div>
                <div style={{ display: 'flex', gap: '10px' }}>
                    {/* UI Cleanup: Removed Paginated View and PDF buttons as requested */}
                </div>
            </div>

            {/* Content */}
            <div ref={contentRef} style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', alignItems: 'center', background: '#000' }}>
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
                        {pages.length === 0 && !loading && !error && (
                            <div style={{ padding: '50px', textAlign: 'center', opacity: 0.5 }}>
                                <p>This chapter seems to be empty or failed to load.</p>
                            </div>
                        )}

                        {pages.map((p, i) => (
                            <img
                                key={i}
                                src={`${API_BASE}/api/manga/image-proxy?url=${encodeURIComponent(p.img || p)}`}
                                alt={`Page ${i + 1}`}
                                style={{
                                    width: '100%',
                                    display: 'block',
                                    height: 'auto',
                                    minHeight: '200px',
                                    background: '#111'
                                }}
                                loading={i < 3 ? "eager" : "lazy"}
                                onError={(e) => {
                                    console.warn(`Failed to load page ${i + 1}`);
                                    // Could add a retry button or secondary proxy here
                                    e.target.style.opacity = 0.5;
                                }}
                            />
                        ))}

                        {/* Navigation Buttons */}
                        <div style={{
                            display: 'flex',
                            justifyContent: 'center',
                            gap: '20px',
                            padding: '40px 0',
                            borderTop: '1px solid rgba(255,255,255,0.1)',
                            marginTop: '20px'
                        }}>
                            {prevChapter && (
                                <button
                                    onClick={() => handleChapterSwitch(prevChapter)}
                                    style={{
                                        background: 'rgba(255,255,255,0.05)',
                                        border: '1px solid rgba(255,255,255,0.1)',
                                        color: 'white',
                                        padding: '12px 24px',
                                        borderRadius: '30px',
                                        cursor: 'pointer',
                                        transition: 'all 0.2s',
                                        fontSize: '0.95rem',
                                        fontWeight: '500'
                                    }}
                                    onMouseEnter={(e) => e.target.style.background = 'rgba(255,255,255,0.1)'}
                                    onMouseLeave={(e) => e.target.style.background = 'rgba(255,255,255,0.05)'}
                                >
                                    ← Previous Chapter
                                </button>
                            )}
                            {nextChapter && (
                                <button
                                    onClick={() => handleChapterSwitch(nextChapter)}
                                    style={{
                                        background: 'var(--primary, #6366f1)',
                                        border: 'none',
                                        color: 'white',
                                        padding: '12px 24px',
                                        borderRadius: '30px',
                                        cursor: 'pointer',
                                        transition: 'all 0.2s',
                                        fontSize: '0.95rem',
                                        fontWeight: '600',
                                        boxShadow: '0 4px 15px rgba(99, 102, 241, 0.3)'
                                    }}
                                    onMouseEnter={(e) => e.target.style.transform = 'translateY(-2px)'}
                                    onMouseLeave={(e) => e.target.style.transform = 'translateY(0)'}
                                >
                                    Next Chapter →
                                </button>
                            )}
                        </div>
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
