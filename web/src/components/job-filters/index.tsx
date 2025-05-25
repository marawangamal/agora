// components/job-filters.tsx - Enhanced filtering
'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import { useState } from 'react';

interface JobFiltersProps {
  groups: string[];
  totalJobs: number;
  filteredCount: number;
}

export function JobFilters({ groups, totalJobs, filteredCount }: JobFiltersProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [search, setSearch] = useState(searchParams.get('search') || '');

  const updateFilter = (key: string, value: string) => {
    const params = new URLSearchParams(searchParams);
    if (value) {
      params.set(key, value);
    } else {
      params.delete(key);
    }
    router.push(`?${params.toString()}`);
  };

  const clearFilters = () => {
    setSearch('');
    router.push('/');
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    updateFilter('search', search);
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 mb-8">
      <div className="flex flex-col lg:flex-row gap-4">
        {/* Search */}
        <form onSubmit={handleSearchSubmit} className="flex-1">
          <div className="relative">
            <input
              type="text"
              placeholder="Search jobs, commands, or IDs..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <span className="text-gray-400">🔍</span>
            </div>
          </div>
        </form>

        {/* Status Filter */}
        <select
          value={searchParams.get('status') || ''}
          onChange={(e) => updateFilter('status', e.target.value)}
          className="px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="">All Statuses</option>
          <option value="COMPLETED">✅ Completed</option>
          <option value="RUNNING">▶️ Running</option>
          <option value="PENDING">⏸️ Pending</option>
          <option value="FAILED">❌ Failed</option>
          <option value="BLOCKED">⛔ Blocked</option>
        </select>

        {/* Group Filter */}
        <select
          value={searchParams.get('group') || ''}
          onChange={(e) => updateFilter('group', e.target.value)}
          className="px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="">All Groups</option>
          {groups.map(group => (
            <option key={group} value={group}>📁 {group}</option>
          ))}
        </select>

        {/* Clear Filters */}
        <button
          onClick={clearFilters}
          className="px-6 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
        >
          Clear
        </button>
      </div>

      {/* Filter Results */}
      <div className="mt-4 text-sm text-gray-600">
        Showing <strong>{filteredCount}</strong> of <strong>{totalJobs}</strong> jobs
        {filteredCount !== totalJobs && (
          <span className="ml-2 text-blue-600">
            ({totalJobs - filteredCount} filtered out)
          </span>
        )}
      </div>
    </div>
  );
}