import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';
import { writeFile, mkdir } from 'fs/promises';

export async function POST(request: NextRequest) {
  try {
    console.log("Starting upload process..."); // Debug log

    // Create input directory if it doesn't exist
    const inputDir = path.join(process.cwd(), '..', 'backend', 'data', 'input');
    console.log("Input directory:", inputDir); // Debug log
    
    try {
      await mkdir(inputDir, { recursive: true });
      console.log("Input directory created/verified"); // Debug log
    } catch (mkdirError) {
      console.error("Error creating directory:", mkdirError);
      return NextResponse.json(
        { error: 'Failed to create input directory', details: mkdirError },
        { status: 500 }
      );
    }

    const formData = await request.formData();
    const files = formData.getAll('documents');
    console.log("Number of files received:", files.length); // Debug log

    if (!files.length) {
      return NextResponse.json(
        { error: 'No files uploaded' },
        { status: 400 }
      );
    }

    // Process each file
    const uploadPromises = files.map(async (file: any) => {
      console.log("Processing file:", file.name); // Debug log
      const bytes = await file.arrayBuffer();
      const buffer = Buffer.from(bytes);
      const filePath = path.join(inputDir, file.name);
      await writeFile(filePath, buffer);
      console.log("File written to:", filePath); // Debug log
      return file.name;
    });

    const uploadedFiles = await Promise.all(uploadPromises);
    console.log("Files uploaded:", uploadedFiles); // Debug log

    // Run the Python script
    console.log("Starting Python script..."); // Debug log
    const pythonScriptPath = path.join(process.cwd(), '..', 'backend', 'store_chunks.py');
    console.log("Python script path:", pythonScriptPath); // Debug log

    const pythonProcess = spawn('python', [pythonScriptPath]);

    return new Promise((resolve) => {
      let result = '';
      let error = '';

      pythonProcess.stdout.on('data', (data) => {
        const output = data.toString();
        console.log("Python stdout:", output); // Debug log
        result += output;
      });

      pythonProcess.stderr.on('data', (data) => {
        const errorOutput = data.toString();
        console.error("Python stderr:", errorOutput); // Debug log
        error += errorOutput;
      });

      pythonProcess.on('close', (code) => {
        console.log("Python process closed with code:", code); // Debug log
        if (code !== 0) {
          resolve(NextResponse.json(
            { 
              message: 'Upload completed but processing failed',
              details: error,
              success: false,
              code: code
            },
            { status: 500 }
          ));
        } else {
          resolve(NextResponse.json({
            message: 'Files uploaded and processed successfully',
            details: result,
            success: true,
            uploadedFiles: uploadedFiles
          }));
        }
      });
    });

  } catch (error) {
    console.error('Upload error:', error);
    return NextResponse.json(
      { 
        error: 'Failed to process upload',
        details: error instanceof Error ? error.message : 'Unknown error',
        stack: error instanceof Error ? error.stack : undefined
      },
      { status: 500 }
    );
  }
}

export const config = {
  api: {
    bodyParser: false,
  },
}; 