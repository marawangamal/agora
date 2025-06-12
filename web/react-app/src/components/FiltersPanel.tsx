import React from 'react';

export default function FiltersPanel() {
  return (
    <div className="filters-panel">
      <div className="filters-title">🔍 Filters &amp; Search</div>

      <div className="filter-section">
        <label className="filter-label">Search Jobs</label>
        <input
          type="text"
          className="search-input"
          id="search-input"
          placeholder="Search by job ID, command, or group..."
        />
      </div>

      <div className="filter-section">
        <label className="filter-label">Status</label>
        <div className="filter-chips" id="status-filters">
          <div className="filter-chip" data-status="RUNNING">
            <span className="status-icon icon-running"></span> Running
          </div>
          <div className="filter-chip" data-status="COMPLETED">
            <span className="status-icon icon-completed"></span> Completed
          </div>
          <div className="filter-chip" data-status="FAILED">
            <span className="status-icon icon-failed"></span> Failed
          </div>
          <div className="filter-chip" data-status="PENDING">
            <span className="status-icon icon-pending"></span> Pending
          </div>
        </div>
      </div>

      <div className="filter-section">
        <label className="filter-label">Groups</label>
        <div className="filter-chips" id="group-filters">
          {/* Dynamically populated */}
        </div>
      </div>

      <div className="filter-section">
        <label className="filter-label">Dependencies</label>
        <div className="filter-chips">
          <div className="filter-chip" data-dependency="has-deps">
            Has Dependencies
          </div>
          <div className="filter-chip" data-dependency="no-deps">
            No Dependencies
          </div>
          <div className="filter-chip" data-dependency="root">
            Root Jobs
          </div>
        </div>
      </div>

      <button className="clear-filters" id="clear-filters-btn">
        Clear All Filters
      </button>

      <div className="filter-stats" id="filter-stats">
        <div className="filter-stats-item">
          <span>Visible Groups:</span>
          <span id="visible-groups">0</span>
        </div>
        <div className="filter-stats-item">
          <span>Total Jobs:</span>
          <span id="visible-jobs">0</span>
        </div>
        <div className="filter-stats-item">
          <span>Filtered Out:</span>
          <span id="filtered-jobs">0</span>
        </div>
      </div>
    </div>
  );
}
