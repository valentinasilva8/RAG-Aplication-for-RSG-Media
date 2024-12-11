"use client";

import { useState } from 'react';

export default function FileUpload() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<any | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file first');
      return;
    }

    setUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      console.log('Attempting upload...');

      const response = await fetch('http://localhost:8000/upload', {
        method: 'POST',
        body: formData,
        mode: 'cors',
        headers: {
          'Accept': 'application/json',
        },
      });

      console.log('Response received:', response.status);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Error response:', errorText);
        throw new Error(`Upload failed: ${response.status} ${response.statusText} - ${errorText}`);
      }

      const data = await response.json();
      console.log('Response data:', data);
      
      if (data.status === 'success') {
        setResults(data.processing_results);
      } else {
        throw new Error(data.error || 'Upload failed');
      }
    } catch (err) {
      console.error('Upload error:', err);
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="p-4">
      <div className="mb-4">
        <input
          type="file"
          accept=".pdf"
          onChange={handleFileChange}
          className="block w-full text-sm text-gray-500
            file:mr-4 file:py-2 file:px-4
            file:rounded-full file:border-0
            file:text-sm file:font-semibold
            file:bg-blue-50 file:text-blue-700
            hover:file:bg-blue-100"
        />
      </div>

      <button
        onClick={handleUpload}
        disabled={!file || uploading}
        className={`px-4 py-2 rounded ${
          !file || uploading
            ? 'bg-gray-300 cursor-not-allowed'
            : 'bg-blue-500 hover:bg-blue-600'
        } text-white font-semibold`}
      >
        {uploading ? 'Uploading...' : 'Upload'}
      </button>

      {error && (
        <div className="mt-4 p-2 bg-red-100 border border-red-400 text-red-700 rounded">
          <pre className="whitespace-pre-wrap">{error}</pre>
        </div>
      )}

      {results && (
        <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded">
          <h3 className="font-semibold mb-2">Processing Results:</h3>
          <pre className="whitespace-pre-wrap">{JSON.stringify(results, null, 2)}</pre>
        </div>
      )}
    </div>
  );
} 