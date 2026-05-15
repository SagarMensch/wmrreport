import http from "node:http";
import https from "node:https";

import { NextRequest, NextResponse } from "next/server";

const BACKEND_CANDIDATES = Array.from(
  new Set(
    [
      "http://127.0.0.1:8005",
      "http://localhost:8005",
      process.env.BACKEND_URL,
    ].filter((value): value is string => Boolean(value)),
  ),
);

const ACTION_MAP: Record<string, (searchParams: URLSearchParams) => string | null> = {
  wells: () => "/api/forecast/wells",
  portfolio: () => "/api/forecast/portfolio",
  well: (searchParams) => {
    const wellId = searchParams.get("id");
    return wellId ? `/api/forecast/well/${encodeURIComponent(wellId)}` : null;
  },
};

export const runtime = "nodejs";
export const maxDuration = 180;

type ProxyResult = {
  body: string;
  statusCode: number;
};

function proxyGet(url: string): Promise<ProxyResult> {
  return new Promise((resolve, reject) => {
    const target = new URL(url);
    const client = target.protocol === "https:" ? https : http;
    const request = client.request(
      target,
      {
        method: "GET",
        headers: {
          Accept: "application/json",
        },
      },
      (response) => {
        let body = "";
        response.setEncoding("utf8");
        response.on("data", (chunk) => {
          body += chunk;
        });
        response.on("end", () => {
          resolve({
            body,
            statusCode: response.statusCode ?? 502,
          });
        });
      },
    );

    request.setTimeout(120_000, () => {
      request.destroy(new Error(`Timed out reaching ${target.origin}`));
    });
    request.on("error", reject);
    request.end();
  });
}

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const action = searchParams.get("action");
    if (!action) {
      return NextResponse.json({ error: "Missing action param" }, { status: 400 });
    }

    const routeBuilder = ACTION_MAP[action];
    if (!routeBuilder) {
      return NextResponse.json({ error: `Unknown action: ${action}` }, { status: 400 });
    }

    const route = routeBuilder(searchParams);
    if (!route) {
      return NextResponse.json({ error: "Missing well id" }, { status: 400 });
    }

    let response: ProxyResult | null = null;
    let lastError: unknown = null;
    for (const backendUrl of BACKEND_CANDIDATES) {
      try {
        response = await proxyGet(`${backendUrl}${route}`);
        break;
      } catch (error) {
        lastError = error;
      }
    }

    if (!response) {
      throw lastError ?? new Error("No reachable backend URL");
    }

    if (response.statusCode < 200 || response.statusCode >= 300) {
      return NextResponse.json(
        { error: `Backend error ${response.statusCode}`, detail: response.body },
        { status: response.statusCode },
      );
    }

    return NextResponse.json(JSON.parse(response.body));
  } catch (error: unknown) {
    const detail = error instanceof Error ? error.message : "Unknown proxy failure";
    console.error("Forecast API Proxy Error:", error);
    return NextResponse.json({ error: detail }, { status: 500 });
  }
}
