// app/page.tsx - Enhanced dashboard
import { getJobs } from "@/actions/jobs";
import { RefreshButton } from "@/components/refresh-button";
import { JobGraph } from "@/components/job-graph";
import { JobFilters } from "@/components/job-filters";
import { JobActions } from "@/components/job-actions";
import { JobDetails } from "@/components/job-details";
import { Suspense } from "react";

interface SearchParams {
  status?: string;
  group?: string;
  search?: string;
}

export default async function Home({ 
  searchParams 
}: { 
  searchParams: SearchParams 
}) {
  const { jobs, error } = await getJobs();

  // Apply filters
  const filteredJobs = jobs.filter(job => {
    if (searchParams.status && job.status !== searchParams.status) return false;
    if (searchParams.group && job.group_name !== searchParams.group) return false;
    if (searchParams.search) {
      const searchLower = searchParams.search.toLowerCase();
      return (
        job.command.toLowerCase().includes(searchLower) ||
        job.job_id.toString().includes(searchLower) ||
        job.group_name.toLowerCase().includes(searchLower)
      );
    }
    return true;
  });

  const stats = {
    total: jobs.length,
    completed: jobs.filter(j => j.status === 'COMPLETED').length,
    running: jobs.filter(j => j.status === 'RUNNING').length,
    pending: jobs.filter(j => j.status === 'PENDING').length,
    failed: jobs.filter(j => ['FAILED', 'CANCELLED'].includes(j.status)).length,
    blocked: jobs.filter(j => j.status === 'BLOCKED').length,
  };

  // Get unique groups for filter
  const groups = [...new Set(jobs.map(j => j.group_name).filter(Boolean))];

  const getStatusColor = (status: string) => {
    switch (status.toUpperCase()) {
      case 'COMPLETED': return 'bg-green-100 text-green-800';
      case 'RUNNING': return 'bg-blue-100 text-blue-800';
      case 'PENDING': return 'bg-yellow-100 text-yellow-800';
      case 'FAILED': return 'bg-red-100 text-red-800';
      case 'BLOCKED': return 'bg-purple-100 text-purple-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-4xl font-bold text-gray-900 mb-2">
              🌳 JRun Dashboard
            </h1>
            <p className="text-gray-600">
              Monitoring {jobs.length} jobs across {groups.length} groups
            </p>
          </div>
          <div className="flex gap-3">
            <RefreshButton />
            <JobActions jobs={filteredJobs} />
          </div>
        </div>

        {/* Enhanced Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-6 gap-4 mb-8">
          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold text-gray-800">{stats.total}</div>
                <div className="text-sm text-gray-600">Total Jobs</div>
              </div>
              <div className="text-2xl">📊</div>
            </div>
          </div>
          
          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold text-green-600">{stats.completed}</div>
                <div className="text-sm text-gray-600">Completed</div>
              </div>
              <div className="text-2xl">✅</div>
            </div>
            <div className="mt-2 text-xs text-gray-500">
              {stats.total > 0 ? Math.round((stats.completed / stats.total) * 100) : 0}% success rate
            </div>
          </div>
          
          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold text-blue-600">{stats.running}</div>
                <div className="text-sm text-gray-600">Running</div>
              </div>
              <div className="text-2xl animate-pulse">▶️</div>
            </div>
          </div>
          
          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold text-yellow-600">{stats.pending}</div>
                <div className="text-sm text-gray-600">Pending</div>
              </div>
              <div className="text-2xl">⏸️</div>
            </div>
          </div>
          
          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold text-purple-600">{stats.blocked}</div>
                <div className="text-sm text-gray-600">Blocked</div>
              </div>
              <div className="text-2xl">⛔</div>
            </div>
          </div>
          
          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold text-red-600">{stats.failed}</div>
                <div className="text-sm text-gray-600">Failed</div>
              </div>
              <div className="text-2xl">❌</div>
            </div>
          </div>
        </div>

        {/* Filters */}
        <JobFilters 
          groups={groups} 
          totalJobs={jobs.length}
          filteredCount={filteredJobs.length}
        />

        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-800 rounded-xl">
            <div className="flex items-center">
              <span className="text-red-500 mr-2">⚠️</span>
              <strong>Error:</strong> {error}
            </div>
          </div>
        )}

        {/* Main Content */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
          {/* Dependency Graph - Takes 2 columns */}
          <div className="xl:col-span-2">
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
              <div className="px-6 py-4 bg-gray-50 border-b border-gray-100">
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                    🔗 Dependency Graph
                  </h2>
                  <div className="text-sm text-gray-500">
                    {filteredJobs.length} jobs shown
                  </div>
                </div>
              </div>
              <div className="p-6">
                <Suspense fallback={<div className="h-96 flex items-center justify-center">Loading graph...</div>}>
                  <JobGraph jobs={filteredJobs} />
                </Suspense>
              </div>
            </div>
          </div>

          {/* Jobs List - Takes 1 column */}
          <div className="space-y-6">
            {/* Job Details Panel */}
            <JobDetails jobs={filteredJobs} />
            
            {/* Compact Jobs List */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
              <div className="px-6 py-4 bg-gray-50 border-b border-gray-100">
                <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                  📋 Jobs ({filteredJobs.length})
                </h2>
              </div>
              
              <div className="max-h-96 overflow-y-auto">
                {filteredJobs.length === 0 ? (
                  <div className="p-8 text-center text-gray-500">
                    <div className="text-4xl mb-2">🔍</div>
                    <div>No jobs match your filters</div>
                  </div>
                ) : (
                  <div className="divide-y divide-gray-100">
                    {filteredJobs.map((job) => (
                      <div key={job.job_id} className="p-4 hover:bg-gray-50 transition-colors">
                        <div className="flex items-center justify-between mb-2">
                          <div className="font-mono text-sm text-blue-600 font-semibold">
                            #{job.job_id}
                          </div>
                          <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(job.status)}`}>
                            {job.status}
                          </span>
                        </div>
                        
                        {job.group_name && (
                          <div className="text-xs text-gray-500 mb-1">
                            📁 {job.group_name}
                          </div>
                        )}
                        
                        <div className="text-sm font-mono text-gray-800 truncate" title={job.command}>
                          {job.command}
                        </div>
                        
                        {job.depends_on.length > 0 && (
                          <div className="mt-2 text-xs text-gray-500">
                            ⬅️ Depends on: {job.depends_on.join(', ')}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}





