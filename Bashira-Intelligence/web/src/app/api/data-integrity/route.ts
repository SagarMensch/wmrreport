import { NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://127.0.0.1:8005";
export const runtime = "nodejs";
export const maxDuration = 120;

export async function GET(request: Request) {
  try {
    const requestUrl = new URL(request.url);
    const search = requestUrl.search || "";
    const timeout = AbortSignal.timeout(120000);
    const response = await fetch(`${BACKEND_URL}/api/data-integrity${search}`, {
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

    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("text/csv")) {
      const csv = await response.text();
      return new Response(csv, {
        status: response.status,
        headers: {
          "Content-Type": "text/csv; charset=utf-8",
          "Content-Disposition":
            response.headers.get("content-disposition") ||
            'attachment; filename="data_integrity.csv"',
        },
      });
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
