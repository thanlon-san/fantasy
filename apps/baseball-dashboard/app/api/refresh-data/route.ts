import { NextResponse } from 'next/server'

export async function POST() {
  try {
    const token = process.env.GITHUB_TOKEN
    const repo = process.env.GITHUB_REPOSITORY || 'thanlon-san/fantasy'
    
    if (!token) {
      return NextResponse.json(
        { error: 'GitHub token not configured', message: 'GITHUB_TOKEN environment variable is missing' },
        { status: 500 }
      )
    }
    
    // Trigger GitHub Actions workflow using repository_dispatch
    const response = await fetch(
      `https://api.github.com/repos/${repo}/dispatches`,
      {
        method: 'POST',
        headers: {
          'Accept': 'application/vnd.github.v3+json',
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          event_type: 'refresh-data',
          client_payload: {
            triggered_by: 'dashboard',
            timestamp: new Date().toISOString(),
          },
        }),
      }
    )
    
    if (!response.ok) {
      const error = await response.text()
      console.error('GitHub API error:', error)
      return NextResponse.json(
        { 
          error: 'Failed to trigger workflow', 
          message: `GitHub API returned ${response.status}`,
          details: error 
        },
        { status: response.status }
      )
    }
    
    return NextResponse.json({
      success: true,
      message: 'Data refresh triggered successfully',
      estimatedTime: '2-3 minutes',
    })
    
  } catch (error) {
    console.error('Refresh error:', error)
    return NextResponse.json(
      { 
        error: 'Internal server error', 
        message: error instanceof Error ? error.message : 'Unknown error' 
      },
      { status: 500 }
    )
  }
}
