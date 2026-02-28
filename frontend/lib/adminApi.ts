import api from './api';

// Types
export interface AdminStats {
  total_users: number;
  total_videos: number;
  total_guests: number;
  total_chats: number;
  videos_ready: number;
  videos_failed: number;
  videos_processing: number;
  today_users: number;
  today_videos: number;
  today_guests: number;
}

export interface UserListItem {
  id: string;
  name: string | null;
  email: string;
  videos_count: number;
  chats_count: number;
  video_limit: number;
  videos_analyzed: number;
  created_at: string;
  last_active: string | null;
}

export interface VideoListItem {
  id: string;
  title: string | null;
  status: string;
  user_name: string | null;
  user_email: string | null;
  is_guest: boolean;
  created_at: string;
  duration_seconds: number | null;
}

export interface GuestListItem {
  id: string;
  guest_token: string;
  video_title: string | null;
  video_status: string | null;
  youtube_id: string | null;
  created_at: string;
}

export interface UserDetail {
  id: string;
  name: string | null;
  email: string;
  avatar_url: string | null;
  videos_analyzed: number;
  video_limit: number;
  created_at: string;
  videos: Array<{
    id: string;
    title: string | null;
    status: string;
    created_at: string;
  }>;
  recent_chats: Array<{
    id: string;
    role: string;
    content: string;
    created_at: string;
  }>;
}

// Admin API calls
export const adminApi = {
  // Get dashboard stats
  getStats: async (): Promise<AdminStats> => {
    const response = await api.get('/api/admin/stats');
    return response.data;
  },

  // Get users list
  getUsers: async (limit = 50, offset = 0): Promise<{ users: UserListItem[]; total: number }> => {
    const response = await api.get('/api/admin/users', {
      params: { limit, offset }
    });
    return response.data;
  },

  // Get single user detail
  getUserDetail: async (userId: string): Promise<UserDetail> => {
    const response = await api.get(`/api/admin/users/${userId}`);
    return response.data;
  },

  // Get videos list
  getVideos: async (limit = 50, offset = 0, status?: string): Promise<{ videos: VideoListItem[]; total: number }> => {
    const response = await api.get('/api/admin/videos', {
      params: { limit, offset, status_filter: status }
    });
    return response.data;
  },

  // Get guests list
  getGuests: async (limit = 50, offset = 0): Promise<{ guests: GuestListItem[]; total: number }> => {
    const response = await api.get('/api/admin/guests', {
      params: { limit, offset }
    });
    return response.data;
  }
};
