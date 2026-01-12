/**
 * Shalom - UI state store using Zustand
 */

import { create } from 'zustand';

interface UIState {
  // Modal states
  isCreateJobModalOpen: boolean;
  isCreateClassModalOpen: boolean;

  // File browser state
  currentBrowsePath: string;
  selectedFiles: string[];

  // Actions
  openCreateJobModal: () => void;
  closeCreateJobModal: () => void;
  openCreateClassModal: () => void;
  closeCreateClassModal: () => void;
  setBrowsePath: (path: string) => void;
  setSelectedFiles: (files: string[]) => void;
  addSelectedFile: (file: string) => void;
  removeSelectedFile: (file: string) => void;
  clearSelectedFiles: () => void;
}

export const useUIStore = create<UIState>((set) => ({
  isCreateJobModalOpen: false,
  isCreateClassModalOpen: false,
  currentBrowsePath: '',
  selectedFiles: [],

  openCreateJobModal: () => set({ isCreateJobModalOpen: true }),
  closeCreateJobModal: () => set({ isCreateJobModalOpen: false, selectedFiles: [] }),
  openCreateClassModal: () => set({ isCreateClassModalOpen: true }),
  closeCreateClassModal: () => set({ isCreateClassModalOpen: false }),
  setBrowsePath: (path) => set({ currentBrowsePath: path }),
  setSelectedFiles: (files) => set({ selectedFiles: files }),
  addSelectedFile: (file) =>
    set((state) => ({
      selectedFiles: state.selectedFiles.includes(file)
        ? state.selectedFiles
        : [...state.selectedFiles, file],
    })),
  removeSelectedFile: (file) =>
    set((state) => ({
      selectedFiles: state.selectedFiles.filter((f) => f !== file),
    })),
  clearSelectedFiles: () => set({ selectedFiles: [] }),
}));
