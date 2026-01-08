import { NextResponse } from 'next/server';

export async function GET() {
  const apiUrl = process.env.API_URL || 'http://localhost:8000';

  try {
    const response = await fetch(`${apiUrl}/api/v1/dashboard/summary`, {
      headers: {
        'Content-Type': 'application/json',
      },
      cache: 'no-store',
    });

    if (!response.ok) {
      return NextResponse.json(
        { error: 'Failed to fetch from API' },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('API fetch error:', error);
    return NextResponse.json(
      { error: 'Failed to connect to API' },
      { status: 500 }
    );
  }
}
