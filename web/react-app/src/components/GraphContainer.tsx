import React from 'react';

export default function GraphContainer() {
  return (
    <div className="graph-container">
      <div className="loading-indicator" id="loading">
        <div>Loading jobs...</div>
      </div>

      <div className="error-indicator" id="error">
        Failed to load jobs. Using dummy data.
      </div>

      <div className="fallback-message" id="fallback">
        <div>Loading graph library...</div>
        <div style={{ marginTop: 8, fontSize: 12 }}>
          If this persists, there may be a network issue.
        </div>
      </div>

      <div className="graph-controls">
        <button className="refresh-btn">↻</button>
        <button>Fit</button>
        <button>+</button>
        <button>-</button>
        <button className="reset-btn">Reset</button>
      </div>

      <div className="graph-info" id="graph-info">
        Showing 0 groups • 0 jobs
      </div>

      <div id="cy"></div>
    </div>
  );
}
