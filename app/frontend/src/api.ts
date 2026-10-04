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
    throw Object.assign(
      new Error(
        typeof body.detail === "string"
          ? body.detail
          : JSON.stringify(body.detail),
      ),
      { status: response.status },
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

// Retry the same staged batch if the connection drops; no duplicate vehicle is created.
let pendingUpload: { signature: string; id: string } | null = null;
export async function uploadPhotos(
  metadata: unknown,
  files: File[],
  progress: (percent: number) => void,
): Promise<{ id: string }> {
  const signature = JSON.stringify([
    metadata,
    files.map((f) => [f.name, f.size, f.lastModified]),
  ]);
  if (pendingUpload && pendingUpload.signature !== signature) {
    const old = await api<{ result: { id: string } | null }>(
      `/uploads/${pendingUpload.id}`,
    ).catch((e) => {
      if (e.status === 404 || e.status === 410) return null;
      throw e;
    });
    if (old?.result) {
      pendingUpload = null;
      return old.result;
    }
    if (old) await api(`/uploads/${pendingUpload.id}`, { method: "DELETE" });
    pendingUpload = null;
  }
  if (!pendingUpload) {
    const batch = await send<{ id: string }>("/uploads", "POST", {
      metadata,
      count: files.length,
    });
    pendingUpload = { signature, id: batch.id };
  }
  const id = pendingUpload.id;
  let status: { received: number[]; result: { id: string } | null };
  try {
    status = await api(`/uploads/${id}`);
  } catch (e) {
    if ([404, 410].includes((e as Error & { status: number }).status))
      pendingUpload = null;
    throw e;
  }
  if (status.result) {
    pendingUpload = null;
    progress(100);
    return status.result;
  }
  const total = files.reduce((sum, f) => sum + f.size, 0);
  let sent = 0;
  for (let i = 0; i < files.length; i++) {
    if (status.received.includes(i)) {
      sent += files[i].size;
      continue;
    }
    const form = new FormData();
    form.append("file", files[i]);
    try {
      await new Promise<void>((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open("PUT", `/api/uploads/${id}/photos/${i}`);
        xhr.timeout = 180000;
        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable)
            progress(
              Math.min(
                99,
                Math.round(
                  ((sent + (files[i].size * e.loaded) / e.total) / total) * 100,
                ),
              ),
            );
        };
        xhr.onerror = xhr.ontimeout = () =>
          reject(
            new Error(
              "Connection interrupted. Keep this page open and submit again to retry the same upload.",
            ),
          );
        xhr.onload = () => {
          if (xhr.status === 404 || xhr.status === 410) pendingUpload = null;
          try {
            const body = JSON.parse(xhr.responseText);
            if (xhr.status >= 200 && xhr.status < 300) resolve();
            else
              reject(
                new Error(
                  typeof body.detail === "string"
                    ? body.detail
                    : "Upload failed. Retry after checking the connection.",
                ),
              );
          } catch {
            reject(
              new Error(
                "Your login may have expired. Sign in again in another tab, then retry this upload.",
              ),
            );
          }
        };
        xhr.send(form);
      });
    } catch (error) {
      throw error;
    }
    sent += files[i].size;
  }
  const result = await send<{ id: string }>(`/uploads/${id}/complete`, "POST");
  pendingUpload = null;
  progress(100);
  return result;
}
