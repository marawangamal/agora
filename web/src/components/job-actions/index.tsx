// components/job-actions.tsx - Bulk actions
'use client';

interface JobActionsProps {
  jobs: any[];
}

export function JobActions({ jobs }: JobActionsProps) {
  const runningJobs = jobs.filter(j => j.status === 'RUNNING').length;
  const failedJobs = jobs.filter(j => ['FAILED', 'CANCELLED'].includes(j.status)).length;

  return (
    <div className="flex gap-2">
      {failedJobs > 0 && (
        <button className="px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 transition-colors text-sm">
          🔄 Retry Failed ({failedJobs})
        </button>
      )}
      
      {runningJobs > 0 && (
        <button className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-sm">
          ⏹️ Stop Running ({runningJobs})
        </button>
      )}
      
      <button className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors text-sm">
        📤 Submit Job
      </button>
    </div>
  );
}