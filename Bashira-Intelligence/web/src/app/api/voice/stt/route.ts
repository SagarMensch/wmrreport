import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8005';

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    
    // We forward the exact FormData representing the audio Blob to FastAPI
    const response = await fetch(`${BACKEND_URL}/api/voice/stt`, {
      method: 'POST',
      body: formData,
      // No Content-Type header needed; `fetch` sets the multipart boundary automatically for FormData
    });

    if (!response.ok) {
      const errorText = await response.text();
      return NextResponse.json(
        { error: `Backend error: ${response.status}`, detail: errorText },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error: any) {
    return NextResponse.json(
      { error: 'Failed to connect to backend STT', detail: error.message },
      { status: 503 }
    );
  }
}
