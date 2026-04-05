import { create } from "zustand";

interface AppState {
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  sidebarOpen: boolean;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
}

export const useAppStore = create<AppState>((set) => ({
  searchQuery: "",
  setSearchQuery: (query: string) => set({ searchQuery: query }),
  sidebarOpen: false,
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setSidebarOpen: (open: boolean) => set({ sidebarOpen: open }),
}));
