'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { adminApi, AdminStats } from '@/lib/adminApi';

const istDay = (dateStr: string) =>
  new Date(dateStr + 'T00:00:00').toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short' });

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
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-900/40 border border-red-700/60 rounded-xl p-4 text-red-200">
        {error}
      </div>
    );
  }

  if (!stats) return null;

  const statCards = [
    { label: 'Total Users', value: stats.total_users, icon: '👥', href: '/admin/users' },
    { label: 'Total Videos', value: stats.total_videos, icon: '🎬', href: '/admin/videos' },
    { label: 'Guest Sessions', value: stats.total_guests, icon: '👤', href: '/admin/guests' },
    { label: 'Chat Messages', value: stats.total_chats, icon: '💬', href: '/admin/chats' },
  ];

  const successRate = stats.total_videos > 0
    ? Math.round((stats.videos_ready / stats.total_videos) * 100)
    : 0;

  const totalFailed = stats.failure_breakdown.reduce((sum, f) => sum + f.count, 0);
  const maxDaily = Math.max(...stats.daily_videos.map(d => d.total), 1);
  const guestPct = stats.total_videos > 0 ? Math.round((stats.guest_videos / stats.total_videos) * 100) : 0;

  const failureColors: Record<string, string> = {
    'Video too long (>2h)': 'bg-amber-500',
    'No captions available': 'bg-red-500',
    'Transcript API error': 'bg-orange-500',
    'AI generation error': 'bg-purple-500',
    'Other': 'bg-gray-500',
    'Unknown': 'bg-gray-600',
  };

  return (
    <div className="space-y-8">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Dashboard</h1>
          <p className="text-gray-400 mt-1">NoteTube AI Admin Panel · All times in IST</p>
        </div>
        <button
          onClick={loadStats}
          className="px-4 py-2 text-sm bg-gray-800 hover:bg-gray-700 border border-gray-700 text-gray-200 rounded-xl transition-colors"
        >
          ↻ Refresh
        </button>
      </div>

      {/* Main Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((stat) => (
          <Link
            key={stat.label}
            href={stat.href}
            className="bento-tile bg-gray-900/70 rounded-2xl p-5 border border-gray-800"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-400 text-sm">{stat.label}</p>
                <p className="text-3xl font-bold text-white mt-1">{stat.value}</p>
              </div>
              <div className="text-3xl opacity-80">{stat.icon}</div>
            </div>
          </Link>
        ))}
      </div>

      {/* Video Status + Success Rate */}
      <div>
        <h2 className="text-lg font-semibold text-white mb-3">Video Pipeline Health</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-gray-900/70 rounded-2xl p-4 border border-gray-800">
            <p className="text-gray-400 text-sm mb-1">Ready</p>
            <p className="text-2xl font-bold text-green-400">{stats.videos_ready}</p>
          </div>
          <div className="bg-gray-900/70 rounded-2xl p-4 border border-gray-800">
            <p className="text-gray-400 text-sm mb-1">Processing</p>
            <p className="text-2xl font-bold text-yellow-400">{stats.videos_processing}</p>
          </div>
          <Link href="/admin/videos?status=FAILED" className="bento-tile bg-gray-900/70 rounded-2xl p-4 border border-gray-800">
            <p className="text-gray-400 text-sm mb-1">Failed →</p>
            <p className="text-2xl font-bold text-red-400">{stats.videos_failed}</p>
          </Link>
          <div className="bg-gray-900/70 rounded-2xl p-4 border border-gray-800">
            <p className="text-gray-400 text-sm mb-1">Success Rate</p>
            <p className={`text-2xl font-bold ${successRate >= 80 ? 'text-green-400' : successRate >= 60 ? 'text-yellow-400' : 'text-red-400'}`}>{successRate}%</p>
          </div>
        </div>
      </div>

      {/* Failure Breakdown */}
      <div>
        <h2 className="text-lg font-semibold text-white mb-3">Why Videos Fail</h2>
        <div className="bg-gray-900/70 rounded-2xl border border-gray-800 p-5 space-y-3">
          {stats.failure_breakdown.length === 0 && (
            <p className="text-gray-500 text-sm">No failed videos 🎉</p>
          )}
          {stats.failure_breakdown.map((f) => {
            const pct = totalFailed > 0 ? Math.round((f.count / totalFailed) * 100) : 0;
            return (
              <div key={f.category}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm text-gray-300">{f.category}</span>
                  <span className="text-sm text-gray-400 font-mono">{f.count} · {pct}%</span>
                </div>
                <div className="h-2 rounded-full bg-gray-800 overflow-hidden">
                  <div
                    className={`h-full rounded-full ${failureColors[f.category] || 'bg-gray-500'}`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Last 7 Days */}
      <div>
        <h2 className="text-lg font-semibold text-white mb-3">Last 7 Days (IST)</h2>
        <div className="bg-gray-900/70 rounded-2xl border border-gray-800 p-5">
          <div className="flex items-end gap-3 h-36">
            {stats.daily_videos.map((d) => (
              <div key={d.date} className="flex-1 flex flex-col items-center gap-1 h-full justify-end">
                <span className="text-xs text-gray-300 font-mono">{d.total}</span>
                <div className="w-full flex flex-col justify-end gap-0.5" style={{ height: `${Math.max((d.total / maxDaily) * 100, 4)}%` }}>
                  <div className="w-full bg-green-500/70 rounded-t" style={{ flexGrow: d.ready || 0 }} />
                  {d.failed > 0 && <div className="w-full bg-red-500/70" style={{ flexGrow: d.failed }} />}
                  {(d.total - d.ready - d.failed) > 0 && <div className="w-full bg-yellow-500/50" style={{ flexGrow: d.total - d.ready - d.failed }} />}
                </div>
                <span className="text-[10px] text-gray-500 whitespace-nowrap">{istDay(d.date)}</span>
              </div>
            ))}
          </div>
          <div className="flex items-center gap-4 mt-4 text-xs text-gray-400">
            <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-green-500/70"></span>Ready</span>
            <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-red-500/70"></span>Failed</span>
            <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-yellow-500/50"></span>Other</span>
          </div>
        </div>
      </div>

      {/* Guest vs Signed-in + Today */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-gray-900/70 rounded-2xl border border-gray-800 p-5">
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3">Guest vs Signed-in Videos</h2>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-300">Guests: <span className="font-bold text-white">{stats.guest_videos}</span> ({guestPct}%)</span>
            <span className="text-sm text-gray-300">Users: <span className="font-bold text-white">{stats.user_videos}</span> ({100 - guestPct}%)</span>
          </div>
          <div className="h-3 rounded-full bg-gray-800 overflow-hidden flex">
            <div className="h-full bg-violet-500/80" style={{ width: `${guestPct}%` }} />
            <div className="h-full bg-indigo-500/80" style={{ width: `${100 - guestPct}%` }} />
          </div>
          <p className="text-xs text-gray-500 mt-2">High guest share = signup conversion opportunity</p>
        </div>

        <div className="bg-gray-900/70 rounded-2xl border border-gray-800 p-5">
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3">Today (IST)</h2>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <p className="text-2xl font-bold text-indigo-400">{stats.today_users}</p>
              <p className="text-xs text-gray-400">New Users</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-indigo-400">{stats.today_videos}</p>
              <p className="text-xs text-gray-400">New Videos</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-indigo-400">{stats.today_guests}</p>
              <p className="text-xs text-gray-400">Guest Sessions</p>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Links */}
      <div className="flex gap-3">
        <Link
          href="/admin/users"
          className="bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white px-5 py-2.5 rounded-xl transition-all text-sm font-medium"
        >
          View All Users
        </Link>
        <Link
          href="/admin/videos?status=FAILED"
          className="bg-red-600/80 hover:bg-red-600 text-white px-5 py-2.5 rounded-xl transition-colors text-sm font-medium"
        >
          View Failed Videos
        </Link>
      </div>
    </div>
  );
}
