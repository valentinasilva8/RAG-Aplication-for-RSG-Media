"use client";

import { useState } from "react";
import { Upload, File, X, Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { motion, AnimatePresence } from "framer-motion";
import { uploadDocuments, downloadExcel, extractVariables } from '@/lib/api';
import path from 'path';

interface UploadResponse {
  message: string;
  details: string;
  excel_file?: string;
}

interface ExtractedVariables {
  agreement_type: string;
  contract_status: string;
  license_period: string;
  contract_currency: string;
  region_territory: string;
  licensee_party: string;
  licensee_contact: string;
  licensee_phone: string;
  licensee_email: string;
  licensor_party: string;
  licensor_address: string;
  license_fee: string;
}

interface ExtractionResult {
  pdf_file: string;
  extracted_variables: ExtractedVariables;
  excel_file: string;
}

export default function DocumentUpload() {
  const [files, setFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [excelFile, setExcelFile] = useState<string | null>(null);
  const [extractionResult, setExtractionResult] = useState<ExtractionResult | null>(null);
  const [isExtracting, setIsExtracting] = useState(false);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const droppedFiles = Array.from(e.dataTransfer.files).filter(
      file => file.type === 'application/pdf'
    );
    
    setFiles(prev => [...prev, ...droppedFiles]);
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const newFiles = Array.from(e.target.files).filter(
        file => file.type === 'application/pdf'
      );
      setFiles(prev => [...prev, ...newFiles]);
    }
  };

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleUpload = async () => {
    setIsUploading(true);
    setUploadError("");
    setExcelFile(null);

    try {
      const dataTransfer = new DataTransfer();
      files.forEach(file => dataTransfer.items.add(file));
      const fileList = dataTransfer.files;
      
      console.log('Starting upload for files:', files.map(f => f.name)); // Debug log
      
      const result = await uploadDocuments(fileList);
      console.log('Upload response:', result);  // Debug log
      
      if (!result.success) {
        throw new Error(
          `Upload failed: ${result.message}\nDetails: ${result.details}`
        );
      }
      
      if (result.excel_file) {
        setExcelFile(result.excel_file);
      }
      setFiles([]); // Clear files after successful upload
    } catch (err) {
      console.error('Upload error:', err);
      const errorMessage = err instanceof Error 
        ? `${err.message}\n${err.stack}` 
        : 'Failed to upload documents. Please try again.';
      setUploadError(errorMessage);
    } finally {
      setIsUploading(false);
    }
  };

  const handleDownloadExcel = async () => {
    if (!excelFile) return;
    try {
      await downloadExcel(excelFile);
    } catch (err) {
      console.error('Download error:', err);
      setUploadError('Failed to download Excel file. Please try again.');
    }
  };

  const handleExtract = async () => {
    try {
      setIsExtracting(true);
      const result = await extractVariables();
      setExtractionResult(result);
      
      // If there's an Excel file path in the result, trigger download
      if (result.excel_file) {
        window.location.href = `/api/download/${encodeURIComponent(
          path.basename(result.excel_file)
        )}`;
      }
    } catch (error) {
      console.error('Extraction failed:', error);
    } finally {
      setIsExtracting(false);
    }
  };

  return (
    <Card className="p-6 shadow-md">
      <div
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
          isDragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300'
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <Upload className="mx-auto h-12 w-12 text-gray-400 mb-4" />
        <h3 className="text-lg font-semibold mb-2">Upload Documents</h3>
        <p className="text-sm text-gray-500 mb-4">
          Drag and drop your PDF contracts here, or click to browse
        </p>
        <input
          type="file"
          multiple
          accept=".pdf"
          onChange={handleFileInput}
          className="hidden"
          id="file-upload"
        />
        <Button asChild variant="outline">
          <label htmlFor="file-upload" className="cursor-pointer">
            Browse Files
          </label>
        </Button>
      </div>

      <AnimatePresence>
        {files.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-6"
          >
            <h4 className="font-medium mb-3">Selected Documents</h4>
            <div className="space-y-2">
              {files.map((file, index) => (
                <motion.div
                  key={`${file.name}-${index}`}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                >
                  <div className="flex items-center space-x-3">
                    <File className="h-5 w-5 text-blue-600" />
                    <span className="text-sm text-gray-700">{file.name}</span>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => removeFile(index)}
                    className="text-gray-500 hover:text-red-500"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </motion.div>
              ))}
            </div>

            {uploadError && (
              <p className="text-red-500 text-sm mt-2">{uploadError}</p>
            )}

            <div className="flex gap-4">
              <Button
                onClick={handleUpload}
                disabled={isUploading}
                className="w-full mt-4"
              >
                {isUploading ? (
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                  >
                    <Upload className="h-5 w-5" />
                  </motion.div>
                ) : (
                  "Upload Documents"
                )}
              </Button>

              {excelFile && (
                <Button
                  onClick={handleDownloadExcel}
                  className="w-full mt-4"
                  variant="outline"
                >
                  <Download className="h-5 w-5 mr-2" />
                  Download Excel
                </Button>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <button 
        onClick={handleExtract}
        disabled={isExtracting}
      >
        {isExtracting ? 'Extracting...' : 'Extract Variables'}
      </button>
      
      {extractionResult && (
        <div>
          <h3>Extracted Variables:</h3>
          <pre>{JSON.stringify(extractionResult.extracted_variables, null, 2)}</pre>
        </div>
      )}
    </Card>
  );
}