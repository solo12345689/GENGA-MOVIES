import React, { useState } from 'react';

const SearchBar = ({ onSearch, placeholder = "Search..." }) => {
    const [query, setQuery] = useState('');
    const [history, setHistory] = useState([]);
    const [showHistory, setShowHistory] = useState(false);
    const wrapperRef = React.useRef(null);

    // Load history from localStorage on mount
    React.useEffect(() => {
        try {
            const saved = localStorage.getItem('moviebox_web_history');
            if (saved) {
                setHistory(JSON.parse(saved));
            }
        } catch (e) {
            console.error("Failed to load history", e);
        }

        // Click outside listener
        const handleClickOutside = (event) => {
            if (wrapperRef.current && !wrapperRef.current.contains(event.target)) {
                setShowHistory(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const saveHistory = (newHistory) => {
        setHistory(newHistory);
        localStorage.setItem('moviebox_web_history', JSON.stringify(newHistory));
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        if (query.trim()) {
            const trimmed = query.trim();
            onSearch(trimmed, 'all');
            setShowHistory(false);

            // Add to history (remove duplicates, keep top 5)
            const newHistory = [trimmed, ...history.filter(h => h !== trimmed)].slice(0, 5);
            saveHistory(newHistory);
        }
    };

    const handleHistoryClick = (item) => {
        setQuery(item);
        onSearch(item, 'all');
        setShowHistory(false);
        // Move to top
        const newHistory = [item, ...history.filter(h => h !== item)];
        saveHistory(newHistory);
    };

    const deleteHistoryItem = (e, item) => {
        e.stopPropagation();
        const newHistory = history.filter(h => h !== item);
        saveHistory(newHistory);
    };

    return (
        <div ref={wrapperRef} className="search-container" style={{ position: 'relative' }}>
            <form onSubmit={handleSubmit}>
                <div style={{ position: 'relative' }}>
                    <input
                        type="text"
                        className="input-glass"
                        placeholder={placeholder}
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        onFocus={() => setShowHistory(true)}
                        style={{ paddingRight: '3rem', width: '100%' }}
                    />
                    <button
                        type="submit"
                        style={{
                            position: 'absolute',
                            right: '15px',
                            top: '50%',
                            transform: 'translateY(-50%)',
                            background: 'transparent',
                            border: 'none',
                            color: 'var(--text-muted)',
                            cursor: 'pointer',
                            padding: '5px'
                        }}
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <circle cx="11" cy="11" r="8"></circle>
                            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                        </svg>
                    </button>
                </div>
            </form>

            {/* History Dropdown */}
            {showHistory && history.length > 0 && (
                <div style={{
                    position: 'absolute',
                    top: '100%',
                    left: 0,
                    right: 0,
                    background: 'rgba(18, 18, 22, 0.95)',
                    backdropFilter: 'blur(10px)',
                    border: '1px solid var(--border-glass)',
                    borderTop: 'none',
                    borderRadius: '0 0 12px 12px',
                    zIndex: 100,
                    maxHeight: '400px',
                    overflowY: 'auto',
                    boxShadow: '0 10px 30px rgba(0,0,0,0.5)'
                }}>
                    <div style={{ padding: '8px 12px', fontSize: '0.75rem', color: 'var(--text-muted)', borderBottom: '1px solid rgba(255,255,255,0.05)', display: 'flex', justifyContent: 'space-between' }}>
                        <span>Recent Searches</span>
                        <span style={{ cursor: 'pointer' }} onClick={() => saveHistory([])}>Clear All</span>
                    </div>
                    {history.map((item, idx) => (
                        <div
                            key={idx}
                            onClick={() => handleHistoryClick(item)}
                            style={{
                                padding: '10px 15px',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                                borderBottom: '1px solid rgba(255,255,255,0.05)',
                                color: 'rgba(255,255,255,0.8)',
                                transition: 'background 0.2s'
                            }}
                            onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.05)'}
                            onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                        >
                            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ opacity: 0.5 }}>
                                    <circle cx="12" cy="12" r="10"></circle>
                                    <polyline points="12 6 12 12 16 14"></polyline>
                                </svg>
                                {item}
                            </div>
                            <button
                                onClick={(e) => deleteHistoryItem(e, item)}
                                style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', opacity: 0.5, padding: '4px' }}
                                onMouseEnter={(e) => e.currentTarget.style.opacity = 1}
                                onMouseLeave={(e) => e.currentTarget.style.opacity = 0.5}
                            >
                                x
                            </button>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

export default SearchBar;
