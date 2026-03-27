import { NextRequest, NextResponse } from 'next/server';

export async function POST(req: NextRequest) {
  try {
    const { term, context } = await req.json();

    const res = await fetch('https://api.mistral.ai/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer 63UJcnnWqxq7RIxLcWucvKPCSgR9WLVy`,
      },
      body: JSON.stringify({
        model: 'mistral-small-latest',
        messages: [
          {
            role: 'system',
            content: 'You are a senior data analyst at a Fortune 500 oil & gas company. Explain machine learning and statistical terms in plain business language that a C-suite executive would understand. Rules: 1) Write 2-3 short sentences maximum. 2) Do NOT use any markdown formatting whatsoever — no asterisks, no bold, no headers, no bullet points. 3) Write in plain flowing prose. 4) Focus on what it means for decision-making and business outcomes. 5) Be concise and authoritative like a BlackRock analyst briefing.',
          },
          {
            role: 'user',
            content: `Explain "${term}" to a non-technical executive in plain text.${context ? ` Context: ${context}.` : ''} What does it mean for our well operations portfolio?`,
          },
        ],
        max_tokens: 120,
        temperature: 0.2,
      }),
    });

    if (!res.ok) {
      return NextResponse.json({ explanation: `${term} measures how reliably we can predict well completion timelines. A strong score here means our forecasting engine is giving your operations team trustworthy guidance for resource allocation.` });
    }

    const data = await res.json();
    let explanation = data.choices?.[0]?.message?.content || 'Explanation unavailable.';
    // Strip any remaining markdown formatting
    explanation = explanation.replace(/\*\*/g, '').replace(/\*/g, '').replace(/^#+\s*/gm, '').replace(/^-\s+/gm, '').trim();
    return NextResponse.json({ explanation });
  } catch {
    return NextResponse.json({ explanation: 'Explanation service temporarily unavailable.' });
  }
}
