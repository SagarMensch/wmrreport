import http from "node:http";
import https from "node:https";

import { NextRequest, NextResponse } from "next/server";

const BACKEND_CANDIDATES = Array.from(
  new Set(
    [
      process.env.BACKEND_URL,
      "http://127.0.0.1:8005",
      "http://localhost:8005",
    ].filter((value): value is string => Boolean(value)),
  ),
);

export const runtime = "nodejs";

type ProxyResult = {
  body: string;
  statusCode: number;
};

function proxyRequest(
  url: string,
  method: "GET" | "POST",
  body?: string,
): Promise<ProxyResult> {
  return new Promise((resolve, reject) => {
    const target = new URL(url);
    const client = target.protocol === "https:" ? https : http;
    const request = client.request(
      target,
      {
        method,
        headers: {
          Accept: "application/json",
          ...(body
            ? {
                "Content-Type": "application/json",
                "Content-Length": Buffer.byteLength(body).toString(),
              }
            : {}),
        },
      },
      (response) => {
        let responseBody = "";
        response.setEncoding("utf8");
        response.on("data", (chunk) => {
          responseBody += chunk;
        });
        response.on("end", () => {
          resolve({
            body: responseBody,
            statusCode: response.statusCode ?? 502,
          });
        });
      },
    );

    request.setTimeout(30_000, () => {
      request.destroy(new Error(`Timed out reaching ${target.origin}`));
    });
    request.on("error", reject);
    if (body) {
      request.write(body);
    }
    request.end();
  });
}

async function proxyToBackend(action: string, method: "GET" | "POST", body?: string) {
  let response: ProxyResult | null = null;
  let lastError: unknown = null;
  for (const backendUrl of BACKEND_CANDIDATES) {
    try {
      response = await proxyRequest(`${backendUrl}/predict/${action}`, method, body);
      break;
    } catch (error) {
      lastError = error;
    }
  }

  if (!response) {
    throw lastError ?? new Error("No reachable backend URL");
  }
  return response;
}

export async function POST(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const action = searchParams.get("action");
    if (!action) {
      return NextResponse.json({ error: "Missing action parameter" }, { status: 400 });
    }

    const body = JSON.stringify(await req.json());
    const response = await proxyToBackend(action, "POST", body);
    if (response.statusCode < 200 || response.statusCode >= 300) {
      return NextResponse.json(
        { error: `Upstream error ${response.statusCode}`, detail: response.body },
        { status: response.statusCode },
      );
    }

    return NextResponse.json(JSON.parse(response.body));
  } catch (error: unknown) {
    console.error("Predict API Proxy Error:", error);
    const detail = error instanceof Error ? error.message : "Unknown proxy failure";
    return NextResponse.json({ error: detail }, { status: 500 });
  }
}

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const action = searchParams.get("action");
    if (!action) {
      return NextResponse.json({ error: "Missing action parameter" }, { status: 400 });
    }

    const response = await proxyToBackend(action, "GET");
    if (response.statusCode < 200 || response.statusCode >= 300) {
      return NextResponse.json(
        { error: `Upstream error ${response.statusCode}`, detail: response.body },
        { status: response.statusCode },
      );
    }

    return NextResponse.json(JSON.parse(response.body));
  } catch (error: unknown) {
    console.error("Predict API Proxy Error:", error);
    const detail = error instanceof Error ? error.message : "Unknown proxy failure";
    return NextResponse.json({ error: detail }, { status: 500 });
  }
}
