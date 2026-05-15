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

const ACTION_MAP: Record<string, string> = {
  portfolio: "/api/command-center/portfolio",
  alerts: "/api/command-center/alerts",
  rig_operations: "/api/command-center/rig-operations",
  location_prep: "/api/command-center/location-prep",
  delay_heatmap: "/api/command-center/delay-heatmap",
  field_atlas: "/api/command-center/field-atlas",
  engineering_timeline: "/api/command-center/engineering-timeline",
  watchlist: "/api/command-center/watchlist",
  data_dictionary: "/api/command-center/data-dictionary",
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

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const action = searchParams.get("action");

    if (!action || !(action in ACTION_MAP)) {
      return NextResponse.json(
        { error: `Unsupported action: ${action || "missing"}` },
        { status: 400 },
      );
    }

    let response: ProxyResult | null = null;
    let lastError: unknown = null;
    for (const backendUrl of BACKEND_CANDIDATES) {
      try {
        response = await proxyGet(`${backendUrl}${ACTION_MAP[action]}`);
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

    const payload = JSON.parse(response.body);
    return NextResponse.json(payload);
  } catch (error: unknown) {
    const detail =
      error instanceof Error ? error.message : "Unknown proxy failure";
    return NextResponse.json(
      { error: "Failed to reach command center backend", detail },
      { status: 500 },
    );
  }
}
