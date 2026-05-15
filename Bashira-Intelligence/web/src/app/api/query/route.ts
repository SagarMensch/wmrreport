import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://127.0.0.1:8005";
const QUERY_TIMEOUT_MS = 15 * 60 * 1000;

export const runtime = "nodejs";
export const maxDuration = 900;

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    const response = await fetch(`${BACKEND_URL}/api/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      cache: "no-store",
      signal: AbortSignal.timeout(QUERY_TIMEOUT_MS),
    });

    if (!response.ok) {
      const errorText = await response.text();
      return NextResponse.json(
        { error: `Backend error: ${response.status}`, detail: errorText },
        { status: response.status },
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error: unknown) {
    const err =
      error instanceof Error ? error : new Error("Unknown proxy error");
    const detail =
      err.name === "TimeoutError"
        ? "Query proxy timed out while waiting for the backend. For long Julia/predictive runs, use the direct backend path or increase the proxy timeout."
        : err.message;
    return NextResponse.json(
      { error: "Failed to connect to backend", detail },
      { status: 503 },
    );
  }
}
