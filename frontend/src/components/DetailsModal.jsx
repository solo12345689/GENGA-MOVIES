import React from 'react';

const DetailsModal = ({ item, onClose, onDownload, onStream, progress, serverMode, API_BASE }) => {
    const [selectedSeason, setSelectedSeason] = React.useState(null);
    const [selectedEpisode, setSelectedEpisode] = React.useState(1);
    const [animeEpisodes, setAnimeEpisodes] = React.useState([]);
    const [episodesLoading, setEpisodesLoading] = React.useState(false);
    const [selectedAnimeEp, setSelectedAnimeEp] = React.useState(null);

    React.useEffect(() => {
        if (item && item.animeEpisodes) {
            setAnimeEpisodes(item.animeEpisodes);
            if (item.animeEpisodes.length > 0) {
                setSelectedAnimeEp(item.animeEpisodes[0]);
            }
            setEpisodesLoading(false);
            return; // Skip fetch if data is already present
        }

        setAnimeEpisodes([]); // Clear previous episodes
        setSelectedAnimeEp(null);

        if (item && item.source === 'hianime') {
            const fetchEpisodes = async () => {
                setEpisodesLoading(true);
                const url = `${API_BASE}/api/anime/episodes/${item.id}`;
                console.log(`[DetailsModal] Fetching anime episodes: ${url}`);
                try {
                    const res = await fetch(url);
                    const data = await res.json();
                    if (data.status === 200 && data.data && data.data.episodes) {
                        setAnimeEpisodes(data.data.episodes);
                        if (data.data.episodes.length > 0) {
                            setSelectedAnimeEp(data.data.episodes[0]);
                        }
                    } else {
                        console.warn("[DetailsModal] HiAnime API returned status 200 but no episodes array", data);
                        setAnimeEpisodes([]);
                    }
                } catch (err) {
                    console.error("[DetailsModal] Failed to fetch anime episodes", err);
                    setAnimeEpisodes([]);
                } finally {
                    setEpisodesLoading(false);
                }
            };
            fetchEpisodes();
        }
    }, [item, API_BASE]);

    React.useEffect(() => {
        if (item && item.seasons && item.seasons.length > 0) {
            setSelectedSeason(item.seasons[0]);
            setSelectedEpisode(1);
        }
    }, [item]);

    if (!item) return null;

    const [animeLanguage, setAnimeLanguage] = React.useState('sub');

    const handleStreamClick = () => {
        if (item.source === 'cinecli') {
            alert('Streaming torrents directly is not yet supported. Please download.');
            return;
        }

        if (item.type === 'series') {
            if (selectedSeason && selectedEpisode) {
                onStream({ ...item, type: item.type }, selectedSeason.season_number, selectedEpisode);
            } else {
                alert('Please select a season and episode');
            }
        } else if (item.type === 'anime') {
            // MovieBox anime
            if (item.source === 'moviebox' && item.seasons && item.seasons.length > 0) {
                if (selectedSeason && selectedEpisode) {
                    onStream({ ...item, type: 'anime' }, selectedSeason.season_number, selectedEpisode);
                } else {
                    alert('Please select a season and episode');
                }
            }
            // HiAnime
            else if (selectedAnimeEp) {
                onStream({ ...item, type: 'anime', episodeId: selectedAnimeEp.episodeId, episodeNo: selectedAnimeEp.number, language: animeLanguage });
            } else {
                alert('Please select an episode');
            }
        } else if (item.source === 'hianime') {
            if (selectedAnimeEp) {
                onStream({ ...item, type: 'anime', episodeId: selectedAnimeEp.episodeId, episodeNo: selectedAnimeEp.number, language: animeLanguage });
            } else {
                alert('Please select an episode');
            }
        } else {
            onStream({ ...item, type: 'movie' });
        }
    };

    const handleDownloadClick = (magnetUrl = null) => {
        if (item.source === 'cinecli' && magnetUrl) {
            // Trigger Magnet
            window.location.href = magnetUrl;
            return;
        }

        // Use new Proxy Download for MovieBox
        if (item.source === 'moviebox' && item.type === 'movie') {
            // We need a URL. For MovieBox, we don't have it easily without /api/stream call.
            // But we can construct the proxy download URL if we knew the direct link.
            // For now, let's just trigger the callback which App.jsx handles (falling back to server download)
            // Or better: update App.jsx to handle this better.

            onDownload(item); // App.jsx will handle
            return;
        }

        if (item.type === 'series' || item.type === 'anime') {
            if (selectedSeason && selectedEpisode) {
                onDownload(item, selectedSeason.season_number, selectedEpisode);
            } else {
                alert('Please select a season and episode');
            }
        } else {
            onDownload(item);
        }
    };

    return (
        <div className="modal-backdrop" onClick={onClose}>
            <div className="modal-content animate-fade-in" onClick={e => e.stopPropagation()}>

                <button onClick={onClose} style={{
                    position: 'absolute',
                    top: '15px',
                    right: '15px',
                    background: 'rgba(0,0,0,0.5)',
                    border: 'none',
                    color: 'white',
                    width: '32px',
                    height: '32px',
                    borderRadius: '50%',
                    cursor: 'pointer',
                    zIndex: 20,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '1.2rem'
                }}>×</button>

                <div className="modal-poster-side" style={{
                    flex: '0 0 40%',
                    position: 'relative',
                    minHeight: '300px',
                    height: 'auto'
                }}>
                    {item.poster_url || item.poster ? (
                        <div onClick={item.source !== 'cinecli' ? handleStreamClick : undefined} style={{ cursor: item.source !== 'cinecli' ? 'pointer' : 'default', height: '100%', position: 'relative', zIndex: 0 }}>
                            <img
                                src={item.poster_url || item.poster}
                                alt={item.title}
                                style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                            />
                        </div>
                    ) : null}
                    <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(to right, transparent 80%, var(--bg-surface) 100%)', zIndex: 1 }}></div>
                </div>

                <div className="modal-details-side" style={{
                    flex: '1',
                    padding: '2.5rem',
                    display: 'flex',
                    flexDirection: 'column',
                    maxHeight: '80vh',
                    overflowY: 'auto'
                }}>
                    <h2 style={{ fontSize: '2.5rem', marginBottom: '0.5rem', lineHeight: 1.1 }}>{item.title}</h2>

                    <div style={{ display: 'flex', gap: '1rem', color: 'var(--text-muted)', marginBottom: '2rem', fontSize: '0.95rem', alignItems: 'center', flexWrap: 'wrap' }}>
                        <span style={{ background: 'rgba(255,255,255,0.1)', padding: '2px 8px', borderRadius: '4px' }}>{item.year}</span>
                        <span style={{ textTransform: 'capitalize', color: 'var(--primary)' }}>
                            {item.source === 'cinecli' ? 'Torpedo' : (item.type || 'Movie')}
                        </span>
                        {item.runtime && <span>{item.runtime} min</span>}
                    </div>

                    {item.rating && (
                        <div style={{
                            marginBottom: '2rem',
                            padding: '1.2rem',
                            background: 'rgba(251, 191, 36, 0.1)',
                            border: '1px solid rgba(251, 191, 36, 0.2)',
                            borderRadius: '12px',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '1rem'
                        }}>
                            <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="#fbbf24">
                                <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
                            </svg>
                            <div>
                                <div style={{ fontSize: '1.4rem', fontWeight: '700', color: '#fbbf24', lineHeight: 1 }}>{item.rating}</div>
                                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>IMDB Rating</div>
                            </div>
                        </div>
                    )}

                    {item.description || item.plot ? (
                        <p style={{ lineHeight: '1.7', marginBottom: '2.5rem', color: 'var(--text-dim)', fontSize: '1.05rem' }}>
                            {item.description || item.plot}
                        </p>
                    ) : null}

                    <div style={{ marginTop: 'auto' }}>

                        {/* --- CINECLI TORRENT LIST --- */}
                        {item.source === 'cinecli' && item.torrents && (
                            <div style={{ marginBottom: '2rem' }}>
                                <h3 style={{ marginBottom: '1rem', fontSize: '1.1rem' }}>Available Torrents</h3>
                                <div style={{ display: 'grid', gap: '0.8rem' }}>
                                    {item.torrents.map((t, idx) => (
                                        <div key={idx} style={{
                                            display: 'flex',
                                            justifyContent: 'space-between',
                                            alignItems: 'center',
                                            background: 'rgba(255,255,255,0.05)',
                                            padding: '12px',
                                            borderRadius: '8px',
                                            border: '1px solid var(--border-glass)'
                                        }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                                <span style={{ fontWeight: '600', color: 'var(--primary)' }}>{t.quality}</span>
                                                <span style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>{t.size}</span>
                                                <span style={{ color: '#22c55e', fontSize: '0.85rem' }}>{t.seeds} seeds</span>
                                            </div>
                                            <button
                                                onClick={() => handleDownloadClick(t.magnet)}
                                                style={{
                                                    background: 'transparent',
                                                    border: '1px solid var(--border-glass)',
                                                    color: 'white',
                                                    padding: '6px 12px',
                                                    borderRadius: '6px',
                                                    cursor: 'pointer',
                                                    fontSize: '0.85rem',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: '6px'
                                                }}
                                            >
                                                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                                                Magnet
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* --- MOVIEBOX SEASONS --- */}
                        {item.source === 'moviebox' && (item.type === 'series' || item.type === 'anime') && (
                            <div style={{
                                marginBottom: '2rem',
                                background: 'rgba(255, 255, 255, 0.03)',
                                padding: '1.5rem',
                                borderRadius: '12px',
                                border: '1px solid rgba(255, 255, 255, 0.08)'
                            }}>
                                <h3 style={{ marginBottom: '1rem', fontSize: '1.1rem', marginTop: 0 }}>Select Episode</h3>
                                {item.seasons && item.seasons.length > 0 ? (
                                    <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                                            <label style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Season</label>
                                            <select
                                                value={selectedSeason ? selectedSeason.season_number : ''}
                                                onChange={(e) => {
                                                    const season = item.seasons.find(s => s.season_number === parseInt(e.target.value));
                                                    setSelectedSeason(season);
                                                    setSelectedEpisode(1);
                                                }}
                                                className="input-glass"
                                                style={{ padding: '0.5rem 1rem', minWidth: '120px' }}
                                            >
                                                {item.seasons.map(s => <option key={s.season_number} value={s.season_number} style={{ background: '#000', color: '#fff' }}>Season {s.season_number}</option>)}
                                            </select>
                                        </div>
                                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                                            <label style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Episode</label>
                                            <select
                                                value={selectedEpisode}
                                                onChange={(e) => setSelectedEpisode(parseInt(e.target.value))}
                                                className="input-glass"
                                                style={{ padding: '0.5rem 1rem', minWidth: '120px' }}
                                            >
                                                {selectedSeason && Array.from({ length: selectedSeason.max_episodes }, (_, i) => i + 1).map(ep => <option key={ep} value={ep} style={{ background: '#000', color: '#fff' }}>Episode {ep}</option>)}
                                            </select>
                                        </div>
                                    </div>
                                ) : (
                                    <p style={{ color: 'var(--text-muted)' }}>Season information not available.</p>
                                )}
                            </div>
                        )}

                        {/* --- HIANIME EPISODES --- */}
                        {item.source === 'hianime' && (
                            <div style={{
                                marginBottom: '2rem',
                                background: 'rgba(255, 255, 255, 0.03)',
                                padding: '1.5rem',
                                borderRadius: '12px',
                                border: '1px solid rgba(255, 255, 255, 0.08)'
                            }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                                    <h3 style={{ margin: 0, fontSize: '1.1rem' }}>Episodes</h3>
                                    <div style={{ display: 'flex', background: 'rgba(255,255,255,0.05)', borderRadius: '8px', padding: '4px' }}>
                                        <button onClick={() => setAnimeLanguage('sub')} style={{ padding: '4px 12px', border: 'none', borderRadius: '6px', cursor: 'pointer', background: animeLanguage === 'sub' ? 'var(--primary)' : 'transparent', color: 'white', fontSize: '0.8rem' }}>SUB</button>
                                        <button onClick={() => setAnimeLanguage('dub')} style={{ padding: '4px 12px', border: 'none', borderRadius: '6px', cursor: 'pointer', background: animeLanguage === 'dub' ? 'var(--primary)' : 'transparent', color: 'white', fontSize: '0.8rem' }}>DUB</button>
                                    </div>
                                </div>
                                {/* Episode Grid */}
                                {animeEpisodes.length > 0 ? (
                                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(50px, 1fr))', gap: '0.5rem', maxHeight: '200px', overflowY: 'auto' }}>
                                        {animeEpisodes.map(ep => (
                                            <button
                                                key={ep.episodeId}
                                                onClick={() => setSelectedAnimeEp(ep)}
                                                style={{
                                                    padding: '0.6rem 0',
                                                    borderRadius: '6px',
                                                    border: '1px solid ' + (selectedAnimeEp?.episodeId === ep.episodeId ? 'var(--primary)' : 'var(--border-glass)'),
                                                    background: selectedAnimeEp?.episodeId === ep.episodeId ? 'var(--primary)' : 'rgba(255,255,255,0.05)',
                                                    color: 'white',
                                                    cursor: 'pointer'
                                                }}
                                            >
                                                {ep.number}
                                            </button>
                                        ))}
                                    </div>
                                ) : (
                                    <p style={{ textAlign: 'center', color: 'var(--text-muted)' }}>{episodesLoading ? 'Loading...' : 'No episodes.'}</p>
                                )}
                            </div>
                        )}

                        {/* --- ACTION BUTTONS (Stream/Download) --- */}
                        {item.source !== 'cinecli' && (
                            <div style={{ display: 'flex', gap: '1rem', marginTop: '1.5rem' }}>
                                <button className="btn btn-primary" onClick={handleStreamClick} style={{ flex: 1 }}>
                                    Stream Now
                                </button>
                                {item.source !== 'hianime' && (
                                    <button className="btn btn-glass" onClick={() => handleDownloadClick()} style={{ flex: 1 }}>
                                        Download
                                    </button>
                                )}
                            </div>
                        )}

                    </div>
                </div>
            </div>
        </div>
    );
};

export default DetailsModal;
