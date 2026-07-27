const BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") || "http://localhost:4000";

export class ApiError extends Error {
  status: number;
  code: string;
  details?: unknown;
  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export type Json = unknown;

type ErrorBody = {
  error?: { code?: string; message?: string; details?: unknown };
};

// Helper outside the conditional flow so TS doesn't narrow branches.
async function readErrorBody(res: Response): Promise<ErrorBody | null> {
  try {
    return (await res.json()) as ErrorBody;
  } catch {
    return null;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      ...(init.headers ?? {}),
    },
  });
  if (res.status === 204) return undefined as T;
  if (!res.ok) {
    const body = await readErrorBody(res);
    const code = body?.error?.code ?? "request_failed";
    const message = body?.error?.message ?? `Request failed (${res.status})`;
    throw new ApiError(res.status, code, message, body?.error?.details);
  }
  return (await res.json()) as T;
}

async function requestForm<T>(path: string, form: FormData): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, { method: "POST", body: form });
  if (res.status === 204) return undefined as T;
  if (!res.ok) {
    const body = await readErrorBody(res);
    throw new ApiError(
      res.status,
      body?.error?.code ?? "upload_failed",
      body?.error?.message ?? "Upload failed"
    );
  }
  return (await res.json()) as T;
}

export const apiClient = { BASE_URL, request, requestForm };
