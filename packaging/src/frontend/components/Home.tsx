'use client';

import DocumentUpload from '@/components/DocumentUpload';

export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-b from-white to-gray-50 py-12">
      <div className="max-w-4xl mx-auto px-4">
        {/* Header */}
        <div className="text-center mb-16">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            <span className="text-blue-600">RSG Media</span> Contract Variable Extractor
          </h1>
          <p className="text-lg text-gray-600 mb-8">
            Upload your contracts to extract and download variables in Excel format
          </p>
        </div>

        {/* Document Upload Section */}
        <DocumentUpload />
      </div>
    </main>
  );
}