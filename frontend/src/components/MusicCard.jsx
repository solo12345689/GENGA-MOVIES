import React from 'react';

const MusicCard = ({ movie, onClick }) => {
    // We reuse the 'movie' prop name to keep consistency with the layout system
    const { title, poster_url, year, type } = movie;

    return (
        <div
            className="movie-card music-card"
            onClick={() => onClick(movie)}
            style={{
                cursor: 'pointer',
                transition: 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                position: 'relative',
                borderRadius: '16px',
                overflow: 'hidden',
                background: 'rgba(255, 255, 255, 0.03)',
                border: '1px solid rgba(255, 255, 255, 0.05)',
                display: 'flex',
                flexDirection: 'column'
            }}
        >
            <div style={{
                position: 'relative',
                aspectRatio: '1/1',
                overflow: 'hidden',
                borderRadius: '12px',
                margin: '12px'
            }}>
                <img
                    src={poster_url || 'https://via.placeholder.com/300?text=No+Cover'}
                    alt={title}
                    style={{
                        width: '100%',
                        height: '100%',
                        objectFit: 'cover',
                        transition: 'transform 0.5s ease'
                    }}
                    onMouseEnter={e => e.currentTarget.style.transform = 'scale(1.1)'}
                    onMouseLeave={e => e.currentTarget.style.transform = 'scale(1)'}
                />

                {/* Play Button Overlay */}
                <div className="play-overlay" style={{
                    position: 'absolute',
                    inset: 0,
                    background: 'rgba(0,0,0,0.4)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    opacity: 0,
                    transition: 'opacity 0.3s ease',
                    backdropFilter: 'blur(4px)'
                }}>
                    <div style={{
                        width: '50px',
                        height: '50px',
                        borderRadius: '50%',
                        background: 'var(--primary)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: 'white',
                        fontSize: '1.5rem',
                        boxShadow: '0 8px 16px rgba(0,0,0,0.3)',
                        transform: 'translateY(10px)',
                        transition: 'transform 0.3s ease'
                    }}>
                        ▶
                    </div>
                </div>
            </div>

            <div style={{ padding: '0 16px 16px 16px' }}>
                <h3 style={{
                    fontSize: '1rem',
                    margin: '0 0 4px 0',
                    color: '#fff',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    fontWeight: '600'
                }}>
                    {title}
                </h3>
                <p style={{
                    fontSize: '0.85rem',
                    margin: 0,
                    color: 'var(--text-muted)',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis'
                }}>
                    {year}
                </p>
            </div>

            <style>{`
                .music-card:hover {
                    background: rgba(255, 255, 255, 0.08);
                    transform: translateY(-5px);
                }
                .music-card:hover .play-overlay {
                    opacity: 1;
                }
                .music-card:hover .play-overlay div {
                    transform: translateY(0);
                }
            `}</style>
        </div>
    );
};

export default MusicCard;
