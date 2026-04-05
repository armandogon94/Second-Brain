"use client";

import { useState, useEffect } from "react";
import useSWR from "swr";
import { useTheme } from "next-themes";
import { toast } from "sonner";
import { Save, Sun, Moon, Monitor } from "lucide-react";
import { Header } from "@/components/Header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchSettings, updateSettings } from "@/lib/api";

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const [llmModel, setLlmModel] = useState("haiku");
  const [saving, setSaving] = useState(false);

  const { data: settings, isLoading } = useSWR("settings", fetchSettings);

  useEffect(() => {
    if (settings) {
      setLlmModel(settings.llm_model || "haiku");
    }
  }, [settings]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateSettings({ llm_model: llmModel });
      toast.success("Settings saved");
    } catch (err) {
      toast.error("Failed to save settings");
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  if (isLoading) {
    return (
      <>
        <Header title="Settings" />
        <div className="p-4 sm:p-6 space-y-6 max-w-2xl mx-auto">
          <Skeleton className="h-48 w-full" />
          <Skeleton className="h-48 w-full" />
        </div>
      </>
    );
  }

  return (
    <>
      <Header title="Settings" />
      <div className="p-4 sm:p-6 space-y-6 max-w-2xl mx-auto">
        {/* LLM Preference */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">LLM Model</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Choose the AI model for search and RAG responses.
            </p>
            <div className="space-y-2">
              {[
                {
                  value: "haiku",
                  label: "Haiku",
                  desc: "Faster responses, lower cost",
                },
                {
                  value: "sonnet",
                  label: "Sonnet",
                  desc: "Higher quality, more detailed answers",
                },
              ].map((option) => (
                <label
                  key={option.value}
                  className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                    llmModel === option.value
                      ? "border-primary bg-primary/5"
                      : "border-border hover:bg-accent"
                  }`}
                >
                  <input
                    type="radio"
                    name="llm-model"
                    value={option.value}
                    checked={llmModel === option.value}
                    onChange={(e) => setLlmModel(e.target.value)}
                    className="accent-primary"
                  />
                  <div>
                    <div className="text-sm font-medium">{option.label}</div>
                    <div className="text-xs text-muted-foreground">
                      {option.desc}
                    </div>
                  </div>
                </label>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Theme */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Appearance</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">
              Choose your preferred color theme.
            </p>
            <div className="flex gap-2">
              {[
                { value: "light", label: "Light", icon: Sun },
                { value: "dark", label: "Dark", icon: Moon },
                { value: "system", label: "System", icon: Monitor },
              ].map((option) => {
                const Icon = option.icon;
                return (
                  <Button
                    key={option.value}
                    variant={theme === option.value ? "default" : "outline"}
                    className="gap-2"
                    onClick={() => setTheme(option.value)}
                  >
                    <Icon className="h-4 w-4" />
                    {option.label}
                  </Button>
                );
              })}
            </div>
          </CardContent>
        </Card>

        {/* Save */}
        <Button onClick={handleSave} disabled={saving} className="gap-2">
          <Save className="h-4 w-4" />
          {saving ? "Saving..." : "Save Settings"}
        </Button>
      </div>
    </>
  );
}
