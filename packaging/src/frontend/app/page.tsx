'use client';

import FileUpload from './components/FileUpload';

export default function Home() {
  return (
    <main className="min-h-screen p-8">
      <h1 className="text-2xl font-bold mb-4">PDF Document Processor</h1>
      <FileUpload />
    </main>
  );
}