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

interface SearchResult {
  answer: string;
  chunks: Array<{
    id: string;
    text: string;
    similarity: number;
    start_page_number: number;
  }>;
  extracted_variables?: ExtractedVariables;
  excel_file?: string;
}

interface ErrorResponse {
  error: string;
}

interface ExtractionResult {
  pdf_file: string;
  extracted_variables: ExtractedVariables;
  excel_file: string;
}

export async function queryDocuments(query: string): Promise<SearchResult> {
  try {
    const response = await fetch('/api/query', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ query }),
    });
    
    const data = await response.json();
    
    if (!response.ok || 'error' in data) {
      throw new Error(data.error || 'Failed to fetch response');
    }
    
    return data as SearchResult;
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
}

export async function uploadDocuments(files: FileList) {
  try {
    const formData = new FormData();
    Array.from(files).forEach((file) => {
      formData.append('documents', file);
    });
    
    const response = await fetch('/api/upload', {
      method: 'POST',
      body: formData,
    });
    
    if (!response.ok) {
      throw new Error('Failed to upload documents');
    }
    
    return await response.json();
  } catch (error) {
    console.error('Upload Error:', error);
    throw error;
  }
}

export async function downloadExcel(filename: string) {
  try {
    const response = await fetch(`/api/download/${filename}`);
    if (!response.ok) throw new Error('Failed to download Excel file');
    
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  } catch (error) {
    console.error('Download Error:', error);
    throw error;
  }
}

export async function extractVariables(): Promise<ExtractionResult> {
  const response = await fetch('/api/extract', {
    method: 'POST',
  });
  
  if (!response.ok) {
    throw new Error('Failed to extract variables');
  }
  
  return response.json();
} 