import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  const apiUrl = process.env.API_URL || 'http://localhost:8000';
  const searchParams = request.nextUrl.searchParams;

  // Forward query parameters
  const queryString = searchParams.toString();
  const url = `${apiUrl}/api/v1/dashboard/weekly-timeline${queryString ? `?${queryString}` : ''}`;

  try {
    const response = await fetch(url, {
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
