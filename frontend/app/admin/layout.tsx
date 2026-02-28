'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/contexts/AuthContext';

// Admin email list (should match backend)
const ADMIN_EMAILS = ['ayushjhanwar12@gmail.com', 'agrawalabhinay25@gmail.com'];

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [authorized, setAuthorized] = useState(false);

  useEffect(() => {
    if (!loading) {
      if (!user) {
        router.push('/dashboard?signin=1');
      } else if (!ADMIN_EMAILS.includes(user.email.toLowerCase())) {
        router.push('/dashboard');
      } else {
        setAuthorized(true);
      }
    }
  }, [user, loading, router]);

  if (loading || !authorized) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-white text-xl">Loading...</div>
      </div>
    );
  }

  const navItems = [
    { href: '/admin', label: 'Dashboard', icon: '📊' },
    { href: '/admin/users', label: 'Users', icon: '👥' },
    { href: '/admin/videos', label: 'Videos', icon: '🎬' },
    { href: '/admin/guests', label: 'Guests', icon: '👤' },
  ];

  return (
    <div className="h-screen bg-gray-900 flex overflow-hidden">
      {/* Sidebar - Fixed */}
      <aside className="w-64 bg-gray-800 border-r border-gray-700 flex flex-col h-screen fixed left-0 top-0">
        <div className="p-4 border-b border-gray-700">
          <Link href="/dashboard" className="flex items-center gap-2">
            <span className="text-2xl">🎓</span>
            <span className="text-white font-bold">NoteTube Admin</span>
          </Link>
        </div>
        <nav className="p-4 flex-1">
          <ul className="space-y-2">
            {navItems.map((item) => (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={`flex items-center gap-3 px-4 py-2 rounded-lg transition-colors ${
                    pathname === item.href
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                  }`}
                >
                  <span>{item.icon}</span>
                  <span>{item.label}</span>
                </Link>
              </li>
            ))}
          </ul>
        </nav>
        <div className="p-4 border-t border-gray-700">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white text-sm">
                {user?.name?.charAt(0) || 'A'}
              </div>
              <div className="text-sm">
                <div className="text-white font-medium">{user?.name}</div>
                <div className="text-gray-400 text-xs">Admin</div>
              </div>
            </div>
            <button
              onClick={() => {
                localStorage.removeItem('token');
                window.location.href = '/';
              }}
              className="text-gray-400 hover:text-red-400 text-sm"
              title="Logout"
            >
              Logout
            </button>
          </div>
        </div>
      </aside>

      {/* Main content - Scrollable */}
      <main className="flex-1 ml-64 h-screen overflow-y-auto">
        <div className="p-8">
          {children}
        </div>
      </main>
    </div>
  );
}
