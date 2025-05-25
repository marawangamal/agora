// app/components/RefreshButton.tsx - Client component for interactivity
'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';

export function RefreshButton() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  const handleRefresh = async () => {
    setLoading(true);
    router.refresh(); // This refreshes the server component
    setTimeout(() => setLoading(false), 1000); // Reset loading state
  };

  return (
    <button
      onClick={handleRefresh}
      disabled={loading}
      className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
    >
      {loading ? 'Loading...' : '🔄 Refresh'}
    </button>
  );
}