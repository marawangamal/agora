// components/job-details.tsx - Quick stats and insights
interface JobDetailsProps {
  jobs: any[];
}

export function JobDetails({ jobs }: JobDetailsProps) {
  if (jobs.length === 0) return null;

  const avgDeps = jobs.reduce((sum, job) => sum + job.depends_on.length, 0) / jobs.length;
  const maxDeps = Math.max(...jobs.map(job => job.depends_on.length));
  const groupCounts = jobs.reduce((acc, job) => {
    const group = job.group_name || 'No Group';
    acc[group] = (acc[group] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
        📈 Job Insights
      </h3>
      
      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <div className="text-gray-500">Avg Dependencies</div>
          <div className="text-lg font-bold text-gray-900">{avgDeps.toFixed(1)}</div>
        </div>
        
        <div>
          <div className="text-gray-500">Max Dependencies</div>
          <div className="text-lg font-bold text-gray-900">{maxDeps}</div>
        </div>
      </div>

      <div className="mt-4">
        <div className="text-gray-500 text-sm mb-2">Top Groups</div>
        <div className="space-y-1">
          {Object.entries(groupCounts)
            .sort(([,a], [,b]) => b - a)
            .slice(0, 3)
            .map(([group, count]) => (
              <div key={group} className="flex justify-between text-sm">
                <span className="truncate">{group}</span>
                <span className="font-medium">{count}</span>
              </div>
            ))}
        </div>
      </div>
    </div>
  );
}