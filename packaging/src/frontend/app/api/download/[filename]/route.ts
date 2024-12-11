import { NextRequest, NextResponse } from 'next/server';
import { readFile } from 'fs/promises';
import path from 'path';

export async function GET(
  request: NextRequest,
  { params }: { params: { filename: string } }
) {
  try {
    const filename = params.filename;
    const rootDir = path.join(process.cwd(), '..');
    const filePath = path.join(rootDir, 'backend', 'excel_outputs', filename);
    
    const fileBuffer = await readFile(filePath);
    
    return new NextResponse(fileBuffer, {
      headers: {
        'Content-Type': 'application/vnd.ms-excel',
        'Content-Disposition': `attachment; filename="${filename}"`,
      },
    });
  } catch (error) {
    console.error('Download error:', error);
    return NextResponse.json(
      { error: 'Failed to download file' },
      { status: 500 }
    );
  }
} 