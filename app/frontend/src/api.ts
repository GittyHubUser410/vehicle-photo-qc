import { useEffect, useState } from "react";

export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...options,
    headers: {
      ...(options.body && !(options.body instanceof FormData)
        ? { "Content-Type": "application/json" }
        : {}),
      ...options.headers,
    },
  });
  if (!response.ok) {
    const body = await response
      .json()
      .catch(() => ({ detail: response.statusText }));
    throw new Error(
      typeof body.detail === "string"
        ? body.detail
        : JSON.stringify(body.detail),
    );
  }
  return response.json();
}
export const send = <T>(path: string, method: string, body?: unknown) =>
  api<T>(path, {
    method,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
let shotLabels: Record<string, string> = {};
export const setShotLabels = (labels: Record<string, string>) => {
  shotLabels = labels;
};
export const label = (value: string) =>
  (value !== "unknown" && shotLabels[value]) ||
  value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .replace("34", "¾");
export const thumbnail = (id: string) => `/api/photos/${id}/thumbnail`;
export const localDate = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};
export const vehicleName = (s: {
  year: number | null;
  make: string;
  model: string;
}) =>
  [s.year, s.make, s.model].filter(Boolean).join(" ") ||
  "Vehicle details not entered";

export function useStored<T>(
  key: string,
  initial: T,
  persistent = false,
): [T, (next: T | ((prev: T) => T)) => void] {
  const storage = persistent ? localStorage : sessionStorage;
  const [value, setValue] = useState<T>(() => {
    try {
      const saved = storage.getItem(key);
      return saved ? JSON.parse(saved) : initial;
    } catch {
      return initial;
    }
  });
  useEffect(() => {
    try {
      storage.setItem(key, JSON.stringify(value));
    } catch {
      /* Private browsing may disable storage. */
    }
  }, [key, value, storage]);
  return [value, setValue];
}

export function uploadPhotos(
  metadata: unknown,
  files: File[],
  progress: (percent: number) => void,
): Promise<{ id: string }> {
  return new Promise((resolve, reject) => {
    const form = new FormData();
    form.append("metadata", JSON.stringify(metadata));
    files.forEach((file) => form.append("files", file));
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/shoots");
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) progress(Math.round((e.loaded / e.total) * 100));
    };
    xhr.onerror = () =>
      reject(
        new Error(
          "Upload connection failed. Check that the local server is running.",
        ),
      );
    xhr.onload = () => {
      try {
        const body = JSON.parse(xhr.responseText);
        if (xhr.status >= 200 && xhr.status < 300) resolve(body);
        else
          reject(
            new Error(
              typeof body.detail === "string"
                ? body.detail
                : JSON.stringify(body.detail),
            ),
          );
      } catch {
        reject(new Error("The server could not finish this upload."));
      }
    };
    xhr.send(form);
  });
}
