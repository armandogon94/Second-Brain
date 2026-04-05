"use client";

import { Menu } from "lucide-react";
import { Button } from "@/components/ui/button";
import { SearchBar } from "@/components/SearchBar";
import { useAppStore } from "@/lib/store";

interface HeaderProps {
  title?: string;
}

export function Header({ title }: HeaderProps) {
  const { toggleSidebar } = useAppStore();

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-4 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 px-4 sm:px-6">
      <Button
        variant="ghost"
        size="icon"
        className="lg:hidden"
        onClick={toggleSidebar}
      >
        <Menu className="h-5 w-5" />
        <span className="sr-only">Toggle menu</span>
      </Button>

      {title && (
        <h1 className="text-lg font-semibold md:text-xl">{title}</h1>
      )}

      <div className="ml-auto hidden md:block w-full max-w-sm">
        <SearchBar />
      </div>
    </header>
  );
}
