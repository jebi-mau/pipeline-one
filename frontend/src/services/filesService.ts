/**
 * Pipeline One - Files API service
 */

import api from './api';
import type { DirectoryContents, FileMetadata, FrameCountResponse } from '../types';

export const filesService = {
  browse: async (path?: string, includeMetadata = false, showAllFiles = false): Promise<DirectoryContents> => {
    const { data } = await api.get('/files/browse', {
      params: { path, include_metadata: includeMetadata, show_all_files: showAllFiles },
    });
    return data;
  },

  getMetadata: async (filePath: string): Promise<FileMetadata> => {
    const { data } = await api.get('/files/metadata', {
      params: { file_path: filePath },
    });
    return data;
  },

  validate: async (filePath: string): Promise<{ path: string; valid: boolean; message: string }> => {
    const { data } = await api.post('/files/validate', null, {
      params: { file_path: filePath },
    });
    return data;
  },

  /**
   * Get frame count for one or more SVO2 files.
   * This is a fast operation that reads from the SVO2 header.
   */
  getFrameCount: async (paths: string[]): Promise<FrameCountResponse> => {
    const { data } = await api.get('/files/frame-count', {
      params: { paths },
      paramsSerializer: {
        indexes: null, // Use paths=a&paths=b format instead of paths[0]=a
      },
    });
    return data;
  },
};
