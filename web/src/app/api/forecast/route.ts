import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8005";

// GET /api/forecast?action=wells | portfolio | well&id=XXXXX
export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const action = searchParams.get("action");
    if (!action) {
      return NextResponse.json({ error: "Missing action param" }, { status: 400 });
    }

    let url = "";
    if (action === "wells") {
      url = `${BACKEND_URL}/api/forecast/wells`;
    } else if (action === "portfolio") {
      url = `${BACKEND_URL}/api/forecast/portfolio`;
    } else if (action === "well") {
      const wellId = searchParams.get("id");
      if (!wellId) {
        return NextResponse.json({ error: "Missing well id" }, { status: 400 });
      }
      url = `${BACKEND_URL}/api/forecast/well/${encodeURIComponent(wellId)}`;
    } else {
      return NextResponse.json({ error: `Unknown action: ${action}` }, { status: 400 });
    }

    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) {
      const text = await response.text();
      throw new Error(`Backend ${response.status}: ${text}`);
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error: any) {
    console.error("Forecast API Proxy Error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
