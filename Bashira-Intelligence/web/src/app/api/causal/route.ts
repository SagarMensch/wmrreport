import { NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://127.0.0.1:8005";
export const runtime = "nodejs";
export const maxDuration = 180;

export async function GET() {
  try {
    const timeout = AbortSignal.timeout(180000);
    const response = await fetch(`${BACKEND_URL}/api/causal/command`, {
      method: "GET",
      cache: "no-store",
      signal: timeout,
    });

    if (!response.ok) {
      const detail = await response.text();
      return NextResponse.json(
        { error: `Backend error: ${response.status}`, detail },
        { status: response.status },
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error: unknown) {
    const detail = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json(
      { error: "Failed to connect to backend", detail },
      { status: 503 },
    );
  }
}
