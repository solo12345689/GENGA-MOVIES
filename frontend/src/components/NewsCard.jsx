import React from 'react';

const NewsCard = ({ item, onClick }) => {
    const handleCardClick = (e) => {
        // Only trigger if not clicking the actual link (if we keep it)
        onClick && onClick(item);
    };

    return (
        <div className="news-card"
            onClick={handleCardClick}
            style={{
                background: 'rgba(255, 255, 255, 0.03)',
                backdropFilter: 'blur(10px)',
                border: '1px solid rgba(255, 255, 255, 0.05)',
                borderRadius: '20px',
                overflow: 'hidden',
                display: 'flex',
                flexDirection: 'column',
                transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
                cursor: 'pointer',
                height: '100%',
                position: 'relative'
            }}>
            <div style={{
                position: 'relative',
                width: '100%',
                paddingTop: '56.25%', // 16:9 Aspect Ratio
                overflow: 'hidden'
            }}>
                <img
                    src={item.thumbnail}
                    alt={item.title}
                    style={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        width: '100%',
                        height: '100%',
                        objectFit: 'cover',
                        transition: 'transform 0.6s ease'
                    }}
                    className="news-thumb"
                />
                <div style={{
                    position: 'absolute',
                    top: '12px',
                    left: '12px',
                    background: 'rgba(0, 0, 0, 0.6)',
                    backdropFilter: 'blur(4px)',
                    padding: '4px 12px',
                    borderRadius: '8px',
                    fontSize: '0.75rem',
                    color: 'var(--primary)',
                    fontWeight: '600',
                    zIndex: 2,
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                    border: '1px solid rgba(var(--primary-rgb), 0.3)'
                }}>
                    {item.topics && item.topics[0] ? item.topics[0] : 'News'}
                </div>
            </div>

            <div style={{
                padding: '1.5rem',
                display: 'flex',
                flexDirection: 'column',
                flex: 1,
                gap: '1rem'
            }}>
                <div style={{
                    color: 'var(--text-muted)',
                    fontSize: '0.8rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px'
                }}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
                    {item.uploadedAt}
                </div>

                <h3 style={{
                    fontSize: '1.1rem',
                    fontWeight: '600',
                    lineHeight: '1.4',
                    margin: 0,
                    color: '#fff',
                    display: '-webkit-box',
                    WebkitLineClamp: 3,
                    WebkitBoxOrient: 'vertical',
                    overflow: 'hidden'
                }}>
                    {item.title}
                </h3>

                <div style={{ flex: 1 }}></div>

                <div
                    style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '8px',
                        color: 'var(--primary)',
                        fontSize: '0.9rem',
                        fontWeight: '600',
                        marginTop: 'auto',
                        transition: 'all 0.2s'
                    }}
                    className="read-more-btn"
                >
                    Read Article
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>
                </div>
            </div>

            <style>{`
                .news-card:hover {
                    transform: translateY(-8px);
                    background: rgba(255, 255, 255, 0.06);
                    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
                    border-color: rgba(var(--primary-rgb), 0.2);
                }
                .news-card:hover .news-thumb {
                    transform: scale(1.1);
                }
                .news-card:hover .read-more-btn {
                    gap: 12px;
                }
            `}</style>
        </div>
    );
};

export default NewsCard;
