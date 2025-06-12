import React, { useState, useEffect } from 'react';

export default function Header() {
  const [theme, setTheme] = useState<'light' | 'dark'>(
    (localStorage.getItem('theme') as 'light' | 'dark') || 'light'
  );

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(theme === 'light' ? 'dark' : 'light');
  };

  return (
    <div className="header">
      <div className="header-content">
        <h1>🔗 SLURM Dependency Graph</h1>
        <p className="subtitle">
          Professional dependency visualization with advanced filtering and live
          log viewing
        </p>
        <div className="copyright">
          <span>© 2024</span>
          <a href="https://github.com/marawangamal/jrun" target="_blank" rel="noreferrer">
            SLURM Visualizer
          </a>
          <span>•</span>
          <span>Built with ❤️ for HPC workflows</span>
          <span>•</span>
          <a href="https://opensource.org/licenses/MIT" target="_blank" rel="noreferrer">
            MIT License
          </a>
        </div>
      </div>
      <div className="header-controls">
        <button className="theme-toggle" onClick={toggleTheme}>
          <span id="theme-icon">{theme === 'dark' ? '☀️' : '🌙'}</span>
          <span id="theme-text">{theme === 'dark' ? 'Light' : 'Dark'}</span>
        </button>
      </div>
    </div>
  );
}
