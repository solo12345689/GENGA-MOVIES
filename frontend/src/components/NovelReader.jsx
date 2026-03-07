import React, { useState, useEffect } from 'react';

const NovelReader = ({ item, chapterId, chapterTitle, API_BASE, onBack, onChapterChange }) => {
    const [content, setContent] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [fontSize, setFontSize] = useState(18);
    const [theme, setTheme] = useState('dark');

    useEffect(() => {
        const fetchChapter = async () => {
            setLoading(true);
            setError(null);
            try {
                // Find chapter URL from item volumes as a fallback
                let chapterUrl = '';
                if (item && item.volumes) {
                    for (const vol of Object.values(item.volumes)) {
                        const ch = vol.find(c => c.id === chapterId);
                        if (ch && ch.url) {
                            chapterUrl = ch.url;
                            break;
                        }
                    }
                }

                const query = `id=${encodeURIComponent(chapterId)}${chapterUrl ? `&url=${encodeURIComponent(chapterUrl)}` : ''}`;
                const res = await fetch(`${API_BASE}/api/novel/chapter?${query}&format=html`);

                if (!res.ok) throw new Error('Failed to load chapter');
                const data = await res.json();
                setContent(data);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };


        if (chapterId) fetchChapter();
    }, [chapterId, API_BASE]);

    const themes = {
        dark: { bg: '#121212', text: '#e0e0e0', card: '#1e1e1e' },
        sepia: { bg: '#f4ecd8', text: '#5b4636', card: '#efe3c0' },
        light: { bg: '#ffffff', text: '#1a1a1a', card: '#f0f0f0' }
    };

    const currentTheme = themes[theme];

    if (loading) {
        return (
            <div style={{
                position: 'fixed', inset: 0, zIndex: 1000,
                background: 'rgba(0,0,0,0.9)', backdropFilter: 'blur(20px)',
                display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: '#fff'
            }}>
                <div className="spinner" style={{ width: '40px', height: '40px', border: '3px solid rgba(255,255,255,0.1)', borderTopColor: 'var(--primary)', borderRadius: '50%', animation: 'spin 1s linear infinite', marginBottom: '1rem' }} />
                <span>Brewing your chapter...</span>
            </div>
        );
    }

    return (
        <div style={{
            position: 'fixed', inset: 0, zIndex: 1000,
            background: currentTheme.bg, color: currentTheme.text,
            overflowY: 'auto', display: 'flex', flexDirection: 'column',
            transition: 'all 0.3s ease'
        }}>
            {/* Header */}
            <header style={{
                position: 'sticky', top: 0,
                background: theme === 'dark' ? 'rgba(0,0,0,0.8)' : 'rgba(255,255,255,0.8)',
                backdropFilter: 'blur(10px)', borderBottom: `1px solid ${theme === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)'}`,
                padding: '1rem 2rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between', zIndex: 10
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <button onClick={onBack} style={{ background: 'transparent', border: 'none', color: 'inherit', cursor: 'pointer', display: 'flex' }}>
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>
                    </button>
                    <div>
                        <h2 style={{ fontSize: '1.2rem', margin: 0 }}>{item.title}</h2>
                        <span style={{ fontSize: '0.9rem', opacity: 0.7 }}>{chapterTitle || 'Reading'}</span>
                    </div>
                </div>

                <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                    {/* Theme Switcher */}
                    <div style={{ display: 'flex', background: 'rgba(255,255,255,0.1)', borderRadius: '20px', padding: '4px' }}>
                        {Object.keys(themes).map(t => (
                            <button
                                key={t}
                                onClick={() => setTheme(t)}
                                style={{
                                    padding: '4px 12px', borderRadius: '16px', border: 'none',
                                    background: theme === t ? 'var(--primary)' : 'transparent',
                                    color: theme === t ? '#fff' : 'inherit', cursor: 'pointer', fontSize: '0.8rem', textTransform: 'capitalize'
                                }}
                            >
                                {t}
                            </button>
                        ))}
                    </div>

                    {/* Font Size Controls */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', opacity: 0.8 }}>
                        <button onClick={() => setFontSize(Math.max(12, fontSize - 2))} style={{ background: 'transparent', border: 'none', color: 'inherit', cursor: 'pointer', fontSize: '1.2rem' }}>A-</button>
                        <span style={{ fontSize: '0.9rem', minWidth: '30px', textAlign: 'center' }}>{fontSize}</span>
                        <button onClick={() => setFontSize(Math.min(32, fontSize + 2))} style={{ background: 'transparent', border: 'none', color: 'inherit', cursor: 'pointer', fontSize: '1.2rem' }}>A+</button>
                    </div>
                </div>
            </header>

            {/* Reading Content */}
            <main style={{
                maxWidth: '800px', margin: '0 auto', padding: '4rem 2rem',
                fontSize: `${fontSize}px`, lineHeight: '1.8', fontFamily: 'Inter, system-ui, sans-serif'
            }}>
                {error ? (
                    <div style={{ textAlign: 'center', padding: '4rem' }}>
                        <h3>Failed to load chapter</h3>
                        <p>{error}</p>
                        <button onClick={() => window.location.reload()} className="btn btn-primary">Retry</button>
                    </div>
                ) : (
                    <div
                        className="novel-content"
                        dangerouslySetInnerHTML={{ __html: content?.body || '' }}
                        style={{ whiteSpace: (content?.format === 'text' || !content?.body?.includes('<p>')) ? 'pre-wrap' : 'normal' }}
                    />
                )}

                {/* Navigation Buttons */}
                <div style={{ marginTop: '4rem', display: 'flex', justifyContent: 'space-between', borderTop: `1px solid ${theme === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)'}`, paddingTop: '2rem' }}>
                    <button
                        disabled={!content?.previous_id}
                        onClick={() => onChapterChange(content.previous_id, 'Previous Chapter')}
                        style={{
                            visibility: content?.previous_id ? 'visible' : 'hidden',
                            background: 'rgba(255,255,255,0.05)',
                            border: '1px solid var(--border-glass)',
                            color: 'inherit',
                            padding: '1rem 2rem',
                            borderRadius: '12px',
                            cursor: 'pointer',
                            transition: 'all 0.2s'
                        }}
                        onMouseEnter={e => e.target.style.background = 'rgba(255,255,255,0.1)'}
                        onMouseLeave={e => e.target.style.background = 'rgba(255,255,255,0.05)'}
                    >
                        Previous Chapter
                    </button>
                    <button
                        disabled={!content?.next_id}
                        onClick={() => onChapterChange(content.next_id, 'Next Chapter')}
                        style={{
                            visibility: content?.next_id ? 'visible' : 'hidden',
                            background: 'var(--primary)',
                            border: 'none',
                            color: '#fff',
                            padding: '1rem 2rem',
                            borderRadius: '12px',
                            cursor: 'pointer',
                            transition: 'all 0.2s',
                            fontWeight: '600'
                        }}
                        onMouseEnter={e => e.target.style.transform = 'translateY(-2px)'}
                        onMouseLeave={e => e.target.style.transform = 'translateY(0)'}
                    >
                        Next Chapter
                    </button>

                </div>
            </main>

            <style>{`
                .novel-content p { margin-bottom: 1.5rem; }
                .novel-content img { max-width: 100%; height: auto; border-radius: 8px; margin: 2rem 0; }
            `}</style>
        </div>
    );
};

export default NovelReader;
