'use client';

import { useAuth } from '@/contexts/AuthContext';

export default function UserProfile() {
  const { user, logout } = useAuth();

  if (!user) return null;

  return (
    <button
      onClick={logout}
      className="px-4 py-2 text-sm bg-red-500 hover:bg-red-600 text-white font-medium rounded-lg transition-colors"
    >
      Sign Out
    </button>
  );
}
