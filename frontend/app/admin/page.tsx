'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { adminApi, AdminStats } from '@/lib/adminApi';

export default function AdminDashboard() {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      setLoading(true);
      const data = await adminApi.getStats();
      setStats(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load stats');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-400">Loading stats...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-900/50 border border-red-500 rounded-lg p-4 text-red-200">
        {error}
      </div>
    );
  }

  if (!stats) return null;

  const statCards = [
    { label: 'Total Users', value: stats.total_users, icon: '👥', color: 'blue', href: '/admin/users' },
    { label: 'Total Videos', value: stats.total_videos, icon: '🎬', color: 'purple', href: '/admin/videos' },
    { label: 'Guest Sessions', value: stats.total_guests, icon: '👤', color: 'green', href: '/admin/guests' },
    { label: 'Chat Messages', value: stats.total_chats, icon: '💬', color: 'yellow' },
  ];

  const videoStatusCards = [
    { label: 'Ready', value: stats.videos_ready, color: 'green' },
    { label: 'Processing', value: stats.videos_processing, color: 'yellow' },
    { label: 'Failed', value: stats.videos_failed, color: 'red' },
  ];

  const todayCards = [
    { label: 'New Users', value: stats.today_users },
    { label: 'New Videos', value: stats.today_videos },
    { label: 'Guest Sessions', value: stats.today_guests },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-white">Dashboard</h1>
        <p className="text-gray-400 mt-1">NoteTube AI Admin Panel</p>
      </div>

      {/* Main Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {statCards.map((stat) => (
          <Link
            key={stat.label}
            href={stat.href || '#'}
            className={`bg-gray-800 rounded-xl p-6 border border-gray-700 hover:border-gray-600 transition-colors ${stat.href ? 'cursor-pointer' : ''}`}
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-400 text-sm">{stat.label}</p>
                <p className="text-3xl font-bold text-white mt-1">{stat.value}</p>
              </div>
              <div className="text-4xl">{stat.icon}</div>
            </div>
          </Link>
        ))}
      </div>

      {/* Video Status */}
      <div>
        <h2 className="text-xl font-semibold text-white mb-4">Video Status</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {videoStatusCards.map((stat) => (
            <div
              key={stat.label}
              className={`bg-gray-800 rounded-lg p-4 border border-gray-700`}
            >
              <div className="flex items-center justify-between">
                <span className="text-gray-400">{stat.label}</span>
                <span className={`text-2xl font-bold ${
                  stat.color === 'green' ? 'text-green-400' :
                  stat.color === 'yellow' ? 'text-yellow-400' :
                  'text-red-400'
                }`}>
                  {stat.value}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Today's Activity */}
      <div>
        <h2 className="text-xl font-semibold text-white mb-4">Today&apos;s Activity</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {todayCards.map((stat) => (
            <div
              key={stat.label}
              className="bg-gray-800 rounded-lg p-4 border border-gray-700"
            >
              <div className="flex items-center justify-between">
                <span className="text-gray-400">{stat.label}</span>
                <span className="text-2xl font-bold text-blue-400">{stat.value}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Quick Links */}
      <div>
        <h2 className="text-xl font-semibold text-white mb-4">Quick Actions</h2>
        <div className="flex gap-4">
          <Link
            href="/admin/users"
            className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg transition-colors"
          >
            View All Users
          </Link>
          <Link
            href="/admin/videos?status=FAILED"
            className="bg-red-600 hover:bg-red-700 text-white px-6 py-3 rounded-lg transition-colors"
          >
            View Failed Videos
          </Link>
          <button
            onClick={loadStats}
            className="bg-gray-700 hover:bg-gray-600 text-white px-6 py-3 rounded-lg transition-colors"
          >
            Refresh Stats
          </button>
        </div>
      </div>
    </div>
  );
}
