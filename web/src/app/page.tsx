// app/page.tsx
'use client';

import { useState } from 'react';

// Simple job type
interface Job {
  id: number;
  command: string;
  status: 'RUNNING' | 'COMPLETED' | 'PENDING' | 'FAILED';
}

// Dummy data
const DUMMY_JOBS: Job[] = [
  { id: 123456, command: 'python train.py --lr 0.001', status: 'COMPLETED' },
  { id: 123457, command: 'python eval.py --model best.pt', status: 'RUNNING' },
  { id: 123458, command: 'python test.py --data test.csv', status: 'PENDING' },
];

export default function Home() {
  const [jobs] = useState<Job[]>(DUMMY_JOBS);

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <h1 className="text-3xl font-bold text-gray-900 mb-8">
          🌳 JRun Dashboard
        </h1>

        {/* Jobs Table */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="px-6 py-4 bg-gray-50 border-b">
            <h2 className="text-lg font-semibold text-gray-900">
              Jobs ({jobs.length})
            </h2>
          </div>
          
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Job ID
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Command
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {jobs.map((job) => (
                <tr key={job.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 text-sm font-mono text-blue-600">
                    {job.id}
                  </td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                      job.status === 'COMPLETED' ? 'bg-green-100 text-green-800' :
                      job.status === 'RUNNING' ? 'bg-blue-100 text-blue-800' :
                      job.status === 'PENDING' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-red-100 text-red-800'
                    }`}>
                      {job.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm font-mono text-gray-900">
                    {job.command}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}