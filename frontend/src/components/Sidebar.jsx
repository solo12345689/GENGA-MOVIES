import React from 'react';

const Sidebar = ({ activeSource, onChangeSource, serverStatus, isOpen, onToggle }) => {
    const navItems = [
        { id: 'home', label: 'Home', icon: <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path> },
        { id: 'moviebox', label: 'MovieBox', icon: <path d="M19.82 2H4.18C2.97 2 2 2.97 2 4.18v15.64C2 21.03 2.97 22 4.18 22h15.64c1.21 0 2.18-.97 2.18-2.18V4.18C22 2.97 21.03 2 19.82 2zM7 16l5-3 5 3V8l-5 3-5-3v8z"></path> },
        { id: 'hianime', label: 'HiAnime', icon: <path d="M12 2L2 7l10 5 10-5-10-5zm0 9l2.5-1.25L12 8.5l-2.5 1.25L12 11zm0 2.5l-5-2.5-5 2.5L12 22l10-8.5-5-2.5-5 2.5z"></path> },
        { id: 'manga', label: 'Manga', icon: <><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path></> }
    ];

    return (
        <aside style={{
            width: isOpen ? '240px' : '70px',
            height: '100vh',
            position: 'sticky',
            top: 0,
            display: 'flex',
            flexDirection: 'column',
            background: 'rgba(0, 0, 0, 0.4)',
            backdropFilter: 'blur(20px)',
            borderRight: '1px solid var(--border-glass)',
            padding: '2rem 1rem',
            zIndex: 100,
            flexShrink: 0,
            transition: 'width 0.3s ease'
        }}>
            {/* Logo Area */}
            <div style={{
                padding: isOpen ? '0 1rem' : '0',
                marginBottom: '3rem',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: isOpen ? 'space-between' : 'center'
            }}>
                {isOpen && (
                    <div>
                        <h1 style={{
                            fontSize: '1.5rem',
                            margin: 0,
                            background: 'linear-gradient(135deg, #fff 0%, var(--primary) 100%)',
                            WebkitBackgroundClip: 'text',
                            WebkitTextFillColor: 'transparent',
                            fontWeight: '800',
                            letterSpacing: '-1px'
                        }}>
                            GENGA
                        </h1>
                        <p style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginTop: '4px', letterSpacing: '2px', textTransform: 'uppercase' }}>Movies</p>
                    </div>
                )}

                <button
                    onClick={onToggle}
                    style={{
                        background: 'transparent',
                        border: 'none',
                        color: 'var(--text-muted)',
                        cursor: 'pointer',
                        padding: '0.5rem',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center'
                    }}
                >
                    {isOpen ? (
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>
                    ) : (
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>
                    )}
                </button>
            </div>

            {/* Navigation */}
            <nav style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {navItems.map(item => (
                    <button
                        key={item.id}
                        onClick={() => onChangeSource(item.id)}
                        title={!isOpen ? item.label : ''}
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: isOpen ? 'flex-start' : 'center',
                            gap: '12px',
                            padding: '12px 16px',
                            background: activeSource === item.id ? 'rgba(255, 255, 255, 0.1)' : 'transparent',
                            border: '1px solid',
                            borderColor: activeSource === item.id ? 'rgba(255,255,255,0.05)' : 'transparent',
                            borderRadius: '12px',
                            color: activeSource === item.id ? '#fff' : 'var(--text-muted)',
                            cursor: 'pointer',
                            transition: 'all 0.2s',
                            textAlign: 'left',
                            fontSize: '0.95rem',
                            fontWeight: activeSource === item.id ? '600' : '400',
                            width: '100%'
                        }}
                        onMouseEnter={e => {
                            if (activeSource !== item.id) {
                                e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)';
                                e.currentTarget.style.color = 'var(--text-secondary)';
                            }
                        }}
                        onMouseLeave={e => {
                            if (activeSource !== item.id) {
                                e.currentTarget.style.background = 'transparent';
                                e.currentTarget.style.color = 'var(--text-muted)';
                            }
                        }}
                    >
                        <svg
                            width="20"
                            height="20"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            style={{ opacity: activeSource === item.id ? 1 : 0.7 }}
                        >
                            {item.icon}
                        </svg>
                        {isOpen && item.label}
                    </button>
                ))}
            </nav>

            {/* Status Footer */}
            <div style={{ marginTop: 'auto', padding: isOpen ? '1rem' : '1rem 0', borderTop: '1px solid var(--border-glass)', display: 'flex', flexDirection: 'column', alignItems: isOpen ? 'flex-start' : 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '0.85rem', color: 'var(--text-muted)', justifyContent: isOpen ? 'flex-start' : 'center' }}>
                    <div style={{
                        width: '8px',
                        height: '8px',
                        borderRadius: '50%',
                        background: serverStatus === 'operational' ? '#22c55e' : '#ef4444',
                        boxShadow: serverStatus === 'operational' ? '0 0 8px #22c55e' : 'none',
                        transition: 'background 0.3s'
                    }}></div>
                    {isOpen && (
                        <span>
                            {serverStatus === 'operational' ? 'Systems Normal' : 'Service Issue'}
                        </span>
                    )}
                </div>
                {isOpen && (
                    <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.2)', marginTop: '6px', marginLeft: '18px' }}>
                        Updated 5m ago
                    </div>
                )}
            </div>
        </aside>
    );
};

export default Sidebar;
