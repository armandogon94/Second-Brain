"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useDebouncedCallback } from "use-debounce";
import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

interface SearchBarProps {
  className?: string;
  defaultValue?: string;
  autoFocus?: boolean;
}

export function SearchBar({ className, defaultValue = "", autoFocus }: SearchBarProps) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [value, setValue] = useState(defaultValue);

  const navigateToSearch = useCallback(
    (query: string) => {
      if (query.trim()) {
        router.push(`/search?q=${encodeURIComponent(query.trim())}`);
      }
    },
    [router]
  );

  const debouncedNavigate = useDebouncedCallback((query: string) => {
    navigateToSearch(query);
  }, 300);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    setValue(newValue);
    if (newValue.trim()) {
      debouncedNavigate(newValue);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      debouncedNavigate.cancel();
      navigateToSearch(value);
    }
  };

  // Cmd+K shortcut to focus
  useEffect(() => {
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    document.addEventListener("keydown", handleGlobalKeyDown);
    return () => document.removeEventListener("keydown", handleGlobalKeyDown);
  }, []);

  return (
    <div className={cn("relative", className)}>
      <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
      <Input
        ref={inputRef}
        type="search"
        placeholder="Search your second brain..."
        className="pl-10 pr-20"
        value={value}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        autoFocus={autoFocus}
      />
      <kbd className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none hidden sm:inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground">
        <span className="text-xs">&#8984;</span>K
      </kbd>
    </div>
  );
}
