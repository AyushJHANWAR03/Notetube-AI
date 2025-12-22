import api from './api';
import {
  Video,
  VideoDetail,
  VideoCreateResponse,
  VideoListResponse,
  VideoStatusResponse,
  SeekResponse,
  UserNote,
  RewriteStyle
} from './types';

/**
 * Guest video creation response (includes additional guest-specific fields)
 */
interface GuestVideoCreateResponse extends VideoCreateResponse {
  is_guest?: boolean;
  guest_token?: string;
}

/**
 * Guest limit check response
 */
interface GuestLimitResponse {
  can_generate: boolean;
  requires_auth: boolean;
  is_cached: boolean;
  tier: string;
}

/**
 * Video API Service
 * Handles all video-related API calls
 */
export const videoApi = {
  /**
   * Submit a YouTube URL for processing (authenticated users)
   */
  async createVideo(url: string): Promise<VideoCreateResponse> {
    const response = await api.post<VideoCreateResponse>('/api/videos', { url });
    return response.data;
  },

  /**
   * Submit a YouTube URL for processing as guest (anonymous users)
   * Returns video info or error if guest limit reached
   */
  async createVideoAsGuest(url: string): Promise<GuestVideoCreateResponse> {
    const response = await api.post<GuestVideoCreateResponse>('/api/videos/guest', { url });
    return response.data;
  },

  /**
   * Check if guest user can create a new video
   */
  async checkGuestLimit(youtubeId?: string): Promise<GuestLimitResponse> {
    const params = youtubeId ? { youtube_id: youtubeId } : {};
    const response = await api.get<GuestLimitResponse>('/guest/check-limit', { params });
    return response.data;
  },

  /**
   * Get all videos for the current user
   */
  async listVideos(params?: {
    limit?: number;
    offset?: number;
    status?: string
  }): Promise<VideoListResponse> {
    const response = await api.get<VideoListResponse>('/api/videos', { params });
    return response.data;
  },

  /**
   * Get video details including notes and transcript
   */
  async getVideo(videoId: string): Promise<VideoDetail> {
    const response = await api.get<VideoDetail>(`/api/videos/${videoId}`);
    return response.data;
  },

  /**
   * Get video processing status
   */
  async getVideoStatus(videoId: string): Promise<VideoStatusResponse> {
    const response = await api.get<VideoStatusResponse>(`/api/videos/${videoId}/status`);
    return response.data;
  },

  /**
   * Delete a video
   */
  async deleteVideo(videoId: string): Promise<void> {
    await api.delete(`/api/videos/${videoId}`);
  },

  /**
   * Reprocess a failed video
   */
  async reprocessVideo(videoId: string): Promise<VideoCreateResponse> {
    const response = await api.post<VideoCreateResponse>(`/api/videos/${videoId}/reprocess`);
    return response.data;
  },

  /**
   * Find timestamp for a topic using AI semantic search ("Take Me There")
   */
  async seekToTopic(videoId: string, query: string): Promise<SeekResponse> {
    const response = await api.post<SeekResponse>(`/api/videos/${videoId}/seek`, { query });
    return response.data;
  },

  // =================== User Notes API ===================

  /**
   * Save a user note from transcript selection
   */
  async saveUserNote(videoId: string, text: string, timestamp: number): Promise<UserNote> {
    const response = await api.post<UserNote>(`/api/videos/${videoId}/user-notes`, {
      text,
      timestamp
    });
    return response.data;
  },

  /**
   * Get all user notes for a video
   */
  async getUserNotes(videoId: string): Promise<UserNote[]> {
    const response = await api.get<UserNote[]>(`/api/videos/${videoId}/user-notes`);
    return response.data;
  },

  /**
   * Delete a user note
   */
  async deleteUserNote(videoId: string, noteId: string): Promise<void> {
    await api.delete(`/api/videos/${videoId}/user-notes/${noteId}`);
  },

  /**
   * Rewrite a note using AI
   */
  async rewriteUserNote(videoId: string, noteId: string, style: RewriteStyle): Promise<UserNote> {
    const response = await api.post<UserNote>(`/api/videos/${videoId}/user-notes/${noteId}/rewrite`, {
      style
    });
    return response.data;
  },

  /**
   * Poll for video status until ready or failed
   */
  async pollVideoStatus(
    videoId: string,
    onProgress?: (video: Video) => void,
    intervalMs: number = 2000,
    maxAttempts: number = 150 // 5 minutes max
  ): Promise<VideoDetail> {
    let attempts = 0;

    return new Promise((resolve, reject) => {
      const poll = async () => {
        try {
          attempts++;
          const statusResponse = await this.getVideoStatus(videoId);
          const { video } = statusResponse;

          if (onProgress) {
            onProgress(video);
          }

          if (video.status === 'READY') {
            // Fetch full video details
            const fullVideo = await this.getVideo(videoId);
            resolve(fullVideo);
          } else if (video.status === 'FAILED') {
            reject(new Error(video.failure_reason || 'Video processing failed'));
          } else if (attempts >= maxAttempts) {
            reject(new Error('Polling timeout - video processing took too long'));
          } else {
            setTimeout(poll, intervalMs);
          }
        } catch (error) {
          reject(error);
        }
      };

      poll();
    });
  }
};

/**
 * Helper to extract video ID from YouTube URL (for thumbnail preview)
 */
export function extractYouTubeVideoId(url: string): string | null {
  const patterns = [
    /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})/,
    /youtube\.com\/shorts\/([a-zA-Z0-9_-]{11})/
  ];

  for (const pattern of patterns) {
    const match = url.match(pattern);
    if (match) return match[1];
  }

  return null;
}

/**
 * Get YouTube thumbnail URL from video ID
 */
export function getYouTubeThumbnail(videoId: string, quality: 'default' | 'hq' | 'maxres' = 'hq'): string {
  const qualityMap = {
    default: 'default',
    hq: 'hqdefault',
    maxres: 'maxresdefault'
  };
  return `https://img.youtube.com/vi/${videoId}/${qualityMap[quality]}.jpg`;
}

/**
 * Format seconds to MM:SS or HH:MM:SS
 */
export function formatDuration(seconds: number): string {
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);

  if (hrs > 0) {
    return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

export default videoApi;
