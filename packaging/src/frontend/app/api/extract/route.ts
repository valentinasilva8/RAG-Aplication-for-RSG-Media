import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';

export async function POST(request: NextRequest) {
  try {
    // Run the Python script
    const pythonProcess = spawn('python', [
      path.join(process.cwd(), '..', 'backend', 'search_chunks.py')
    ]);

    return new Promise((resolve, reject) => {
      let result = '';
      let error = '';

      pythonProcess.stdout.on('data', (data) => {
        result += data.toString();
      });

      pythonProcess.stderr.on('data', (data) => {
        error += data.toString();
      });

      pythonProcess.on('close', (code) => {
        if (code !== 0) {
          resolve(NextResponse.json(
            { error: error || 'Failed to extract variables' },
            { status: 500 }
          ));
        } else {
          try {
            const parsedResult = JSON.parse(result);
            resolve(NextResponse.json(parsedResult));
          } catch (e) {
            resolve(NextResponse.json(
              { error: 'Invalid response format' },
              { status: 500 }
            ));
          }
        }
      });
    });
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to process request' },
      { status: 500 }
    );
  }
} 