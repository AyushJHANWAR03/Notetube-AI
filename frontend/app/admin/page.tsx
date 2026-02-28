'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { adminApi, AdminStats, AdminInsights } from '@/lib/adminApi';

export default function AdminDashboard() {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [insights, setInsights] = useState<AdminInsights | null>(null);
  const [loading, setLoading] = useState(true);
  const [insightsLoading, setInsightsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadStats();
    loadInsights();
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

  const loadInsights = async () => {
    try {
      setInsightsLoading(true);
      const data = await adminApi.getInsights();
      setInsights(data);
    } catch (err: any) {
      console.error('Failed to load insights:', err);
    } finally {
      setInsightsLoading(false);
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

      {/* AI Insights */}
      {insights && (
        <div className="bg-gradient-to-r from-purple-900/50 to-blue-900/50 rounded-xl border border-purple-700 p-6">
          <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
            <span>🤖</span> AI Insights
          </h2>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Summary */}
            <div>
              <h3 className="text-gray-300 font-medium mb-2">Summary</h3>
              <p className="text-gray-400 text-sm whitespace-pre-line">{insights.insights}</p>
            </div>

            {/* Video Categories */}
            <div>
              <h3 className="text-gray-300 font-medium mb-2">Content Categories</h3>
              <div className="space-y-2">
                {insights.video_categories.map((cat) => (
                  <div key={cat.name} className="flex items-center justify-between">
                    <span className="text-gray-400 text-sm">{cat.name}</span>
                    <div className="flex items-center gap-2">
                      <div className="w-32 bg-gray-700 rounded-full h-2">
                        <div
                          className="bg-blue-500 h-2 rounded-full"
                          style={{ width: `${Math.min((cat.count / insights.user_behavior.total_videos) * 100, 100)}%` }}
                        />
                      </div>
                      <span className="text-white text-sm w-8">{cat.count}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Recommendations */}
          <div className="mt-6">
            <h3 className="text-gray-300 font-medium mb-2">Recommendations</h3>
            <ul className="space-y-2">
              {insights.recommendations.map((rec, i) => (
                <li key={i} className="flex items-start gap-2 text-sm">
                  <span className="text-green-400">→</span>
                  <span className="text-gray-400">{rec}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {insightsLoading && (
        <div className="bg-gray-800 rounded-xl border border-gray-700 p-6 animate-pulse">
          <div className="h-4 bg-gray-700 rounded w-32 mb-4"></div>
          <div className="h-20 bg-gray-700 rounded"></div>
        </div>
      )}

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
            onClick={() => { loadStats(); loadInsights(); }}
            className="bg-gray-700 hover:bg-gray-600 text-white px-6 py-3 rounded-lg transition-colors"
          >
            Refresh Stats
          </button>
        </div>
      </div>
    </div>
  );
}
