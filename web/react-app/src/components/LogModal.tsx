import React from 'react';

export default function LogModal() {
  return (
    <div id="log-modal" className="log-modal">
      <div className="log-modal-content">
        <div className="log-modal-header">
          <div className="log-modal-title" id="log-modal-title">job.slurm_out</div>
          <div className="log-controls">
            <button className="tail-toggle-btn" id="tail-toggle-btn">
              <span className="tail-status-icon"></span>
              <span>Tail: OFF</span>
            </button>
            <button className="close-btn">&times;</button>
          </div>
        </div>
        <textarea
          className="log-viewer"
          id="log-viewer"
          readOnly
          placeholder="Loading log file..."
        ></textarea>
        <div className="log-status">
          <div className="log-status-indicator">
            <div className="log-status-dot" id="log-status-dot"></div>
            <span id="log-status-text">Disconnected</span>
          </div>
          <div id="log-info">
            <span id="log-lines">0 lines</span> •
            <span id="log-size">0 bytes</span>
          </div>
        </div>
      </div>
    </div>
  );
}
