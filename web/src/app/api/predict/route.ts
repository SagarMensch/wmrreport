import { NextRequest, NextResponse } from "next/server";

const PREDICT_INTERNAL_URL = "http://localhost:8001";

export async function POST(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const action = searchParams.get("action");
    if (!action) return NextResponse.json({ error: "Missing action parameter" }, { status: 400 });

    const body = await req.json();

    const response = await fetch(`${PREDICT_INTERNAL_URL}/predict/${action}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    
    if (!response.ok) {
        throw new Error(`Upstream error: ${response.statusText}`);
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error: any) {
    console.error("Predict API Proxy Error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

export async function GET(req: NextRequest) {
    try {
        const { searchParams } = new URL(req.url);
        const action = searchParams.get("action");
        if (!action) return NextResponse.json({ error: "Missing action parameter" }, { status: 400 });

        const response = await fetch(`${PREDICT_INTERNAL_URL}/predict/${action}`);
        if (!response.ok) {
            throw new Error(`Upstream error: ${response.statusText}`);
        }
        
        const data = await response.json();
        return NextResponse.json(data);
    } catch (error: any) {
        console.error("Predict API Proxy Error:", error);
        return NextResponse.json({ error: error.message }, { status: 500 });
    }
}
