import { useState } from 'react';
import { 
  Button, 
  Text, 
  VStack, 
  HStack, 
  useToast 
} from '@chakra-ui/react';

const FileUpload = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [processingResults, setProcessingResults] = useState<any>(null);
  const toast = useToast();

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      if (file.type !== 'application/pdf') {
        toast({
          title: 'Invalid file type',
          description: 'Please select a PDF file',
          status: 'error',
          duration: 3000,
          isClosable: true,
        });
        return;
      }
      setSelectedFile(file);
      setProcessingResults(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      toast({
        title: 'No file selected',
        description: 'Please select a file first',
        status: 'warning',
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      // Upload and process the file
      const response = await fetch('http://localhost:8000/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Upload failed');
      }

      const result = await response.json();
      setProcessingResults(result.processing_results);
      
      toast({
        title: 'Success',
        description: 'File uploaded and processed successfully',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });

    } catch (error) {
      toast({
        title: 'Error',
        description: error instanceof Error ? error.message : 'An error occurred',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <VStack spacing={4} align="stretch">
      <HStack spacing={4}>
        <Button as="label" htmlFor="file-upload" colorScheme="blue">
          Choose PDF
          <input
            id="file-upload"
            type="file"
            accept=".pdf"
            onChange={handleFileSelect}
            style={{ display: 'none' }}
          />
        </Button>
        <Button
          colorScheme="green"
          onClick={handleUpload}
          isLoading={isUploading}
          isDisabled={!selectedFile}
        >
          Upload
        </Button>
      </HStack>
      {selectedFile && (
        <Text>Selected file: {selectedFile.name}</Text>
      )}
      {processingResults && (
        <VStack align="stretch" spacing={2}>
          <Text fontWeight="bold">Processing Results:</Text>
          <pre style={{ background: '#f5f5f5', padding: '1rem', borderRadius: '4px' }}>
            {JSON.stringify(processingResults, null, 2)}
          </pre>
        </VStack>
      )}
    </VStack>
  );
};

export default FileUpload; 