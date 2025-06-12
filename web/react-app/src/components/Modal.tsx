import React from 'react';

export default function Modal() {
  return (
    <div id="modal" className="modal">
      <div className="modal-content">
        <div className="modal-header">
          <div>
            <div className="modal-title" id="modal-title">Group Details</div>
            <div className="modal-subtitle" id="modal-subtitle"></div>
            <div className="modal-stats" id="modal-stats"></div>
          </div>
          <button className="close-btn">&times;</button>
        </div>
        <div className="modal-body">
          <div className="job-grid" id="job-grid"></div>
        </div>
      </div>
    </div>
  );
}
