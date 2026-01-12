/**
 * Shalom - File browser hooks using React Query
 */

import { useQuery } from '@tanstack/react-query';
import { filesService } from '../services';

export const fileKeys = {
  browse: (path?: string, showAllFiles = false) => ['files', 'browse', path, showAllFiles] as const,
  metadata: (path: string) => ['files', 'metadata', path] as const,
};

export function useBrowseFiles(path?: string, showAllFiles = false, includeMetadata = false) {
  return useQuery({
    queryKey: fileKeys.browse(path, showAllFiles),
    queryFn: () => filesService.browse(path, includeMetadata, showAllFiles),
  });
}

export function useFileMetadata(filePath: string | undefined) {
  return useQuery({
    queryKey: fileKeys.metadata(filePath!),
    queryFn: () => filesService.getMetadata(filePath!),
    enabled: !!filePath,
  });
}
