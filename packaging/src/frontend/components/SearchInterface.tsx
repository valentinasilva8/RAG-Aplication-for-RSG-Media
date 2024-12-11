"use client";

import { useState } from "react";
import { Search, FileText, ArrowRight, Bot } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { motion, AnimatePresence } from "framer-motion";
import { queryDocuments } from '@/lib/api';

interface SearchResult {
  answer: string;
  chunks: Array<{
    id: string;
    text: string;
    similarity: number;
    start_page_number: number;
  }>;
}

export default function SearchInterface() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<SearchResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!query.trim()) {
      setError("Please enter a question");
      return;
    }
    
    setIsLoading(true);
    setError("");
    setResult(null);
    
    try {
      const response = await queryDocuments(query.trim());
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to get answer');
      console.error('Search error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileUpload = async (files: FileList) => {
    const formData = new FormData();
    Array.from(files).forEach((file) => {
      formData.append('documents', file);
    });

    try {
      const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Failed to upload documents');
      }

      // Handle successful upload
      const data = await response.json();
      console.log('Upload successful:', data);
    } catch (err) {
      console.error('Upload error:', err);
      // Handle upload error
    }
  };

  const sampleQuestions = [
    "Who is the licensor?",
    "What are the payment terms?",
    "When does the contract expire?",
    "What are the licensing rights?"
  ];

  return (
    <div className="space-y-8">
      <Card className="p-8 shadow-lg">
        <form onSubmit={handleSearch} className="space-y-6">
          <div className="relative">
            <Bot className="absolute left-4 top-4 h-6 w-6 text-blue-600" />
            <Input
              type="text"
              placeholder="Ask any question about your legal documents..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="pl-14 pr-4 py-7 text-lg rounded-xl border-2 focus:border-blue-500"
            />
          </div>
          <Button 
            type="submit" 
            size="lg"
            className="w-full bg-blue-600 hover:bg-blue-700 text-lg py-6"
            disabled={isLoading}
          >
            {isLoading ? (
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
              >
                <Search className="h-5 w-5" />
              </motion.div>
            ) : (
              <span className="flex items-center gap-2">
                Search Documents <ArrowRight className="h-5 w-5" />
              </span>
            )}
          </Button>
        </form>
      </Card>

      <AnimatePresence>
        {(result || error) && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
          >
            <Card className={`p-6 shadow-lg border-l-4 ${error ? 'border-l-red-600' : 'border-l-blue-600'}`}>
              <div className="flex items-start gap-4">
                <FileText className={`h-6 w-6 ${error ? 'text-red-600' : 'text-blue-600'} mt-1`} />
                <div className="space-y-4">
                  <div>
                    <h3 className="font-semibold text-gray-900 mb-2">
                      {error ? 'Error:' : 'Answer:'}
                    </h3>
                    <p className="text-gray-700 text-lg">{error || result?.answer}</p>
                  </div>
                  
                  {result?.chunks && (
                    <div>
                      <h4 className="font-medium text-gray-900 mt-4 mb-2">Source Documents:</h4>
                      <div className="space-y-2">
                        {result.chunks.map((chunk) => (
                          <div 
                            key={chunk.id}
                            className="p-3 bg-gray-50 rounded-lg text-sm"
                          >
                            <div className="text-gray-500 mb-1">
                              Page {chunk.start_page_number} • Similarity: {(chunk.similarity * 100).toFixed(1)}%
                            </div>
                            <div className="text-gray-700">{chunk.text}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      <div>
        <h3 className="text-sm font-medium text-gray-500 mb-4">Popular questions:</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {sampleQuestions.map((question) => (
            <Button
              key={question}
              variant="outline"
              className="justify-start h-auto py-3 px-4 text-left"
              onClick={() => setQuery(question)}
            >
              <Search className="h-4 w-4 mr-2 flex-shrink-0" />
              {question}
            </Button>
          ))}
        </div>
      </div>
    </div>
  );
}