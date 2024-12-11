import { NextRequest, NextResponse } from 'next/server';
import { exec } from 'child_process';
import { promisify } from 'util';
import path from 'path';

const execAsync = promisify(exec);

export const dynamic = 'force-dynamic';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { query } = body;
    
    if (!query) {
      return NextResponse.json({ error: 'Query is required' }, { status: 400 });
    }

    // Escape the query string to handle special characters
    const escapedQuery = query.replace(/"/g, '\\"');
    
    // Get the absolute path to the Python script and its directory
    const scriptPath = path.join(process.cwd(), '../backend/search_chunks.py');
    const scriptDir = path.dirname(scriptPath);
    
    console.log('Executing Python script:', scriptPath);
    console.log('Script directory:', scriptDir);
    
    // Call the Python script with the query, ensuring we're in the correct directory
    const { stdout, stderr } = await execAsync(
      `cd "${scriptDir}" && python "${scriptPath}" "${escapedQuery}"`
    );
    
    if (stderr) {
      console.error('Python script error:', stderr);
      return NextResponse.json({ error: 'Failed to process query' }, { status: 500 });
    }
    
    try {
      // Parse the JSON output from Python
      const result = JSON.parse(stdout.trim());
      
      // Check if there's an error in the result
      if ('error' in result) {
        return NextResponse.json({ error: result.error }, { status: 500 });
      }
      
      return NextResponse.json(result);
    } catch (parseError) {
      console.error('Failed to parse Python output:', stdout);
      return NextResponse.json({ error: 'Invalid response format' }, { status: 500 });
    }
  } catch (error) {
    console.error('Error:', error);
    return NextResponse.json(
      { error: 'Failed to process query' },
      { status: 500 }
    );
  }
} 