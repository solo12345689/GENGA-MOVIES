import React, { useState, useEffect } from 'react';

const NewsReader = ({ articleId, onClose }) => {
    const [article, setArticle] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchArticle = async () => {
            setLoading(true);
            try {
                const res = await fetch(`https://api-consumet-org-mswp.onrender.com/news/ann/info?id=${encodeURIComponent(articleId)}`);
                if (res.ok) {
                    const data = await res.json();
                    setArticle(data);
                } else {
                    setError("Failed to load article content.");
                }
            } catch (err) {
                setError("An error occurred while fetching the article.");
            } finally {
                setLoading(false);
            }
        };

        if (articleId) fetchArticle();
    }, [articleId]);

    if (!articleId) return null;

    return (
        <div className="news-reader-overlay" style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.85)',
            backdropFilter: 'blur(20px)',
            zIndex: 2000,
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            padding: '2rem',
            animation: 'fadeIn 0.3s ease'
        }}>
            <div className="news-reader-content" style={{
                width: '100%',
                maxWidth: '900px',
                height: '90vh',
                background: 'var(--bg-card)',
                borderRadius: '32px',
                border: '1px solid var(--border-glass)',
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden',
                boxShadow: '0 40px 100px rgba(0,0,0,0.8)',
                position: 'relative',
                animation: 'slideUp 0.4s cubic-bezier(0.4, 0, 0.2, 1)'
            }}>
                {/* Header with Close */}
                <div style={{
                    padding: '1.5rem 2rem',
                    borderBottom: '1px solid var(--border-glass)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    background: 'rgba(255,255,255,0.02)',
                    zIndex: 10
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', color: 'var(--primary)', fontWeight: '600' }}>
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2"></path><path d="M18 14h-8"></path><path d="M15 18h-5"></path><path d="M10 6h8v4h-8z"></path></svg>
                        News Reader
                    </div>
                    <button
                        onClick={onClose}
                        style={{
                            background: 'rgba(255,255,255,0.05)',
                            border: 'none',
                            color: 'white',
                            cursor: 'pointer',
                            padding: '8px',
                            borderRadius: '50%',
                            display: 'flex',
                            transition: 'all 0.2s'
                        }}
                        onMouseOver={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.1)'}
                        onMouseOut={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.05)'}
                    >
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                    </button>
                </div>

                {/* Article Area */}
                <div style={{
                    flex: 1,
                    overflowY: 'auto',
                    padding: '0',
                    display: 'flex',
                    flexDirection: 'column'
                }}>
                    {loading ? (
                        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '1.5rem' }}>
                            <div className="spinner-large" style={{
                                width: '48px',
                                height: '48px',
                                border: '4px solid rgba(255,255,255,0.1)',
                                borderTopColor: 'var(--primary)',
                                borderRadius: '50%',
                                animation: 'spin 1s linear infinite'
                            }}></div>
                            <div style={{ color: 'var(--text-muted)' }}>Fetching article content...</div>
                        </div>
                    ) : error ? (
                        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '1rem', color: '#ff4b4b' }}>
                            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
                            <div>{error}</div>
                            <button onClick={onClose} style={{ color: 'white', background: 'var(--primary)', border: 'none', padding: '10px 20px', borderRadius: '8px', cursor: 'pointer', marginTop: '1rem' }}>Back to News</button>
                        </div>
                    ) : article && (
                        <>
                            {/* Hero Banner */}
                            <div style={{ width: '100%', height: '400px', position: 'relative', overflow: 'hidden' }}>
                                <img
                                    src={article.thumbnail}
                                    style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                                    alt="Thumbnail"
                                />
                                <div style={{
                                    position: 'absolute',
                                    inset: 0,
                                    background: 'linear-gradient(to top, var(--bg-card) 0%, transparent 100%)'
                                }}></div>
                            </div>

                            {/* Content */}
                            <div style={{
                                padding: '0 3rem 4rem 3rem',
                                marginTop: '-100px',
                                position: 'relative',
                                display: 'flex',
                                flexDirection: 'column',
                                gap: '2rem'
                            }}>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                                    <h1 style={{ fontSize: '2.8rem', fontWeight: '800', lineHeight: '1.1', color: 'white', margin: 0 }}>
                                        {article.title}
                                    </h1>
                                    <div style={{ color: 'var(--text-muted)', fontSize: '1rem', display: 'flex', gap: '12px', alignItems: 'center' }}>
                                        <span>{article.uploadedAt}</span>
                                        <span style={{ width: '4px', height: '4px', borderRadius: '2px', background: 'rgba(255,255,255,0.2)' }}></span>
                                        <a href={article.url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--primary)', textDecoration: 'none' }}>Source ANN</a>
                                    </div>
                                </div>

                                {article.intro && (
                                    <div style={{
                                        padding: '1.5rem',
                                        background: 'rgba(var(--primary-rgb), 0.1)',
                                        borderRadius: '16px',
                                        borderLeft: '4px solid var(--primary)',
                                        fontStyle: 'italic',
                                        color: 'rgba(255,255,255,0.9)',
                                        fontSize: '1.1rem',
                                        lineHeight: '1.6'
                                    }}>
                                        {article.intro}
                                    </div>
                                )}

                                <div style={{
                                    fontSize: '1.15rem',
                                    lineHeight: '1.8',
                                    color: 'rgba(255,255,255,0.85)',
                                    whiteSpace: 'pre-wrap'
                                }}>
                                    {article.description}
                                </div>
                            </div>
                        </>
                    )}
                </div>
            </div>

            <style>{`
                @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
                @keyframes slideUp { from { transform: translateY(50px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
                .spinner-large {
                    width: '48px', height: '48px',
                    border: '4px solid rgba(255,255,255,0.1)',
                    borderTopColor: 'var(--primary)',
                    borderRadius: '50%',
                    animation: 'spin 1s linear infinite'
                }
                @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
            `}</style>
        </div>
    );
};

export default NewsReader;
