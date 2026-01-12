/**
 * Shalom - Files API service
 */

import api from './api';
import type { DirectoryContents, FileMetadata } from '../types';

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
};
