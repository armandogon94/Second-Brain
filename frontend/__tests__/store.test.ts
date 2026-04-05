import { describe, it, expect } from "vitest";
import { useAppStore } from "@/lib/store";

describe("App Store", () => {
  it("has default search query", () => {
    const state = useAppStore.getState();
    expect(state.searchQuery).toBe("");
  });

  it("updates search query", () => {
    useAppStore.getState().setSearchQuery("test query");
    expect(useAppStore.getState().searchQuery).toBe("test query");
  });

  it("toggles sidebar", () => {
    const initial = useAppStore.getState().sidebarOpen;
    useAppStore.getState().toggleSidebar();
    expect(useAppStore.getState().sidebarOpen).toBe(!initial);
  });
});
