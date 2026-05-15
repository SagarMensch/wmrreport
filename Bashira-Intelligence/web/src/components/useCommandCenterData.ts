"use client";

import { useEffect, useState } from "react";

interface CommandCenterEnvelope<T> {
  status: string;
  data: T;
  error?: string;
  detail?: string;
}

export function useCommandCenterData<T>(action: string, initialData: T) {
  const [data, setData] = useState<T>(initialData);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`/api/command-center?action=${action}`, {
        cache: "no-store",
      });

      const payload = (await response.json()) as CommandCenterEnvelope<T>;
      if (!response.ok) {
        throw new Error(payload.detail || payload.error || "Request failed");
      }

      setData(payload.data);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Unknown request failure";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [action]);

  return { data, loading, error, refresh: load };
}
