import type { ApiResponse } from "../types";

const DEFAULT_API_BASE_URL = "http://localhost:8000/api/v1";

export class ApiClientError extends Error {
  public readonly status: number;
  public readonly details: unknown;

  public constructor(message: string, status: number, details?: unknown) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.details = details;
  }
}

export const apiBaseUrl =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") ?? DEFAULT_API_BASE_URL;

async function parseResponse<T>(response: Response): Promise<ApiResponse<T>> {
  const payload = (await response.json().catch(() => null)) as ApiResponse<T> | null;

  if (!response.ok) {
    const message = payload?.message || `Request failed with HTTP ${response.status}`;
    throw new ApiClientError(message, response.status, payload);
  }

  if (!payload || typeof payload !== "object" || !("data" in payload)) {
    throw new ApiClientError("Invalid API response structure", response.status, payload);
  }

  return payload;
}

export async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    method: "GET",
    headers: {
      Accept: "application/json",
    },
  });
  return (await parseResponse<T>(response)).data;
}

export async function postJson<T>(path: string): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    method: "POST",
    headers: {
      Accept: "application/json",
    },
  });
  return (await parseResponse<T>(response)).data;
}

export async function uploadFile<T>(path: string, file: File): Promise<T> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${apiBaseUrl}${path}`, {
    method: "POST",
    headers: {
      Accept: "application/json",
    },
    body: formData,
  });

  return (await parseResponse<T>(response)).data;
}

function getDownloadFileName(response: Response, fallbackName: string): string {
  const disposition = response.headers.get("Content-Disposition");
  const fileNameMatch = disposition?.match(/filename\*?=(?:UTF-8'')?["']?([^"';]+)["']?/i);
  return fileNameMatch?.[1] ? decodeURIComponent(fileNameMatch[1]) : fallbackName;
}

export async function downloadFile(path: string, fallbackName: string): Promise<void> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    method: "GET",
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as ApiResponse<unknown> | null;
    const message = payload?.message || `Request failed with HTTP ${response.status}`;
    throw new ApiClientError(message, response.status, payload);
  }

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = getDownloadFileName(response, fallbackName);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}
