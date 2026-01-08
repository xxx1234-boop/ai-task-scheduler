import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  const apiUrl = process.env.API_URL || 'http://localhost:8000';
  const searchParams = request.nextUrl.searchParams;
  const period = searchParams.get('period') || 'week';

  try {
    const response = await fetch(
      `${apiUrl}/api/v1/dashboard/stats?period=${period}`,
      {
        headers: {
          'Content-Type': 'application/json',
        },
        cache: 'no-store',
      }
    );

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
