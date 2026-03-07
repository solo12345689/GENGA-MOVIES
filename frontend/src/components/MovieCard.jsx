import React from 'react';

const MovieCard = ({ movie, onClick }) => {
    const poster = movie.poster_url || movie.poster;

    return (
        <div className="movie-card animate-fade-in" onClick={() => onClick(movie)}>
            {poster ? (
                <img
                    src={poster}
                    alt={movie.title}
                    loading="lazy"
                    onError={(e) => {
                        e.target.onerror = null;
                        e.target.style.display = 'none';
                        e.target.nextSibling.style.display = 'flex';
                    }}
                />
            ) : null}
            <div className="poster-placeholder" style={{
                width: '100%',
                height: '100%',
                display: poster ? 'none' : 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--text-muted)',
                background: '#1a1a20',
                flexDirection: 'column',
                gap: '0.5rem'
            }}>
                <span style={{ fontSize: '2rem' }}>🖼️</span>
                <span>No Poster</span>
            </div>
            <div className="movie-card-overlay">
                <h3 style={{ fontSize: '1.1rem', marginBottom: '0.25rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', color: 'white' }}>{movie.title}</h3>
                <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>
                    {movie.source === 'hianime' ? 'Anime' :
                        movie.source === 'manga' ? 'Manga' :
                            movie.source === 'novel' ? 'Novel' :
                                movie.source === 'tv' ? (movie.type === 'country' ? 'Country' : 'Live TV') :
                                    movie.year || 'Unknown Year'}

                </p>
            </div>
        </div>
    );
};

export default MovieCard;
