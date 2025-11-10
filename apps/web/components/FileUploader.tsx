'use client';

import { useState, useCallback, useRef, ChangeEvent, DragEvent, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button, Card } from '@neura/ui';
import { cn } from '@/lib/utils';
import { Upload, File, X, CheckCircle, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';
import { uploadDocument, DocumentUploadResponse } from '@/services/api';

// Type definitions
interface FileValidationError {
  code: string;
  message: string;
}

interface FileUploaderProps {
  onFileSelect?: (file: File) => void;
  onUploadComplete?: (result: DocumentUploadResponse) => void;
  maxSizeMB?: number;
  acceptedTypes?: string[];
  className?: string;
}

// Constants
const ACCEPTED_FILE_TYPES: Record<string, string> = {
  'application/pdf': '.pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
  'text/plain': '.txt',
  'image/png': '.png',
  'image/jpeg': '.jpg',
};

const FILE_TYPE_LABELS: Record<string, string> = {
  'application/pdf': 'PDF',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'DOCX',
  'text/plain': 'TXT',
  'image/png': 'PNG',
  'image/jpeg': 'JPG',
};

export default function FileUploader({
  onFileSelect,
  onUploadComplete,
  maxSizeMB = 10,
  acceptedTypes = [
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/plain',
    'image/png',
    'image/jpeg',
  ],
  className,
}: FileUploaderProps) {
  // Component state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [validationError, setValidationError] = useState<FileValidationError | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadComplete, setUploadComplete] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const activeXhrRef = useRef<XMLHttpRequest | null>(null);

  // Cleanup active XHR on unmount
  useEffect(() => {
    return () => {
      if (activeXhrRef.current) {
        activeXhrRef.current.abort();
        activeXhrRef.current = null;
      }
    };
  }, []);

  // File validation function
  const validateFile = useCallback(
    (file: File): FileValidationError | null => {
      // Check file size
      const maxBytes = maxSizeMB * 1024 * 1024;
      if (file.size > maxBytes) {
        return {
          code: 'FILE_TOO_LARGE',
          message: `File size exceeds ${maxSizeMB}MB limit`,
        };
      }

      // Check file type
      if (!acceptedTypes.includes(file.type)) {
        return {
          code: 'INVALID_FILE_TYPE',
          message: 'File type not supported. Please upload PDF, DOCX, TXT, PNG, or JPG',
        };
      }

      // Extract file extension and verify it matches the MIME type
      const fileName = file.name.toLowerCase();
      const expectedExtension = ACCEPTED_FILE_TYPES[file.type];
      if (expectedExtension && !fileName.endsWith(expectedExtension) && !fileName.endsWith('.jpeg')) {
        return {
          code: 'INVALID_FILE_TYPE',
          message: 'File extension does not match file type',
        };
      }

      return null;
    },
    [acceptedTypes, maxSizeMB]
  );

  // File selection logic (shared by drop and input handlers)
  const handleFileSelection = useCallback(
    (file: File) => {
      const error = validateFile(file);
      
      if (error) {
        setValidationError(error);
        setSelectedFile(null);
      } else {
        setValidationError(null);
        setSelectedFile(file);
        setUploadProgress(0);
        setUploadComplete(false);
        
        if (onFileSelect) {
          onFileSelect(file);
        }
      }
    },
    [validateFile, onFileSelect]
  );

  // Drag-and-drop handlers
  const handleDragEnter = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    
    // Check if we're leaving the drop zone entirely
    const target = e.currentTarget;
    const relatedTarget = e.relatedTarget as Node;
    if (!target.contains(relatedTarget)) {
      setIsDragging(false);
    }
  }, []);

  const handleDragOver = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback(
    (e: DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);

      const files = e.dataTransfer.files;
      if (files.length > 0 && files[0]) {
        handleFileSelection(files[0]);
      }
    },
    [handleFileSelection]
  );

  // File input handler
  const handleFileInputChange = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (files && files.length > 0 && files[0]) {
        handleFileSelection(files[0]);
      }
    },
    [handleFileSelection]
  );

  // Remove file handler
  const handleRemoveFile = useCallback(() => {
    setSelectedFile(null);
    setValidationError(null);
    setUploadProgress(0);
    setUploadComplete(false);
    setIsUploading(false);
    
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, []);

  // Upload file to backend with progress tracking
  const handleUpload = useCallback(async () => {
    if (!selectedFile) return;

    setIsUploading(true);
    setUploadProgress(0);

    const toastId = toast.loading('Uploading document...');

    try {
      const result: DocumentUploadResponse = await uploadDocument(
        selectedFile,
        (progress) => setUploadProgress(progress),
        activeXhrRef
      );

      setUploadComplete(true);
      setIsUploading(false);
      toast.dismiss(toastId);
      toast.success(result.message || 'Document uploaded successfully');

      if (onUploadComplete) {
        onUploadComplete(result);
      }
    } catch (error) {
      setIsUploading(false);
      toast.dismiss(toastId);
      const errorMessage = error instanceof Error ? error.message : 'Failed to upload document';
      toast.error(errorMessage);
      setValidationError({
        code: 'UPLOAD_ERROR',
        message: errorMessage,
      });
    }
  }, [selectedFile, onUploadComplete]);

  // Handle click on drop zone
  const handleDropZoneClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  // Handle keyboard interaction on drop zone
  const handleDropZoneKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLDivElement>) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        fileInputRef.current?.click();
      }
    },
    []
  );

  // Format file size
  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024 * 1024) {
      return `${(bytes / 1024).toFixed(1)} KB`;
    }
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  return (
    <Card className={cn('bg-surface-ui border-border-ui p-6', className)}>
      <AnimatePresence mode="wait">
        {!selectedFile && !uploadComplete && (
          <motion.div
            key="dropzone"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className={cn(
              'border-2 border-dashed rounded-lg p-8 transition-colors cursor-pointer',
              isDragging ? 'border-border-strong bg-black-ui/50' : 'border-border-ui'
            )}
            onDragEnter={handleDragEnter}
            onDragLeave={handleDragLeave}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
            onClick={handleDropZoneClick}
            onKeyDown={handleDropZoneKeyDown}
            role="button"
            tabIndex={0}
            aria-label="Upload file"
          >
            <motion.div
              animate={{
                scale: isDragging ? 1.02 : 1,
              }}
              transition={{ duration: 0.2 }}
              className="flex flex-col items-center justify-center space-y-4"
            >
              <Upload className="w-12 h-12 text-muted-ui" />
              <div className="text-center">
                <p className="text-lg font-semibold text-text-ui mb-1">
                  Drag and drop your file here
                </p>
                <p className="text-sm text-muted-ui mb-2">or click to browse</p>
                <p className="text-xs text-muted-ui">
                  PDF, DOCX, TXT, PNG, JPG (max {maxSizeMB}MB)
                </p>
              </div>

              <input
                ref={fileInputRef}
                type="file"
                accept={acceptedTypes.join(',')}
                onChange={handleFileInputChange}
                className="hidden"
                aria-label="Upload file"
              />

              <Button
                variant="outline"
                onClick={(e) => {
                  e.stopPropagation();
                  fileInputRef.current?.click();
                }}
                className="mt-4"
              >
                Browse Files
              </Button>
            </motion.div>
          </motion.div>
        )}

        {selectedFile && !isUploading && !uploadComplete && (
          <motion.div
            key="selected"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
            className="space-y-4"
          >
            <div className="flex items-start justify-between p-4 bg-black-ui/30 border border-border-ui rounded-lg">
              <div className="flex items-start space-x-3 flex-1 min-w-0">
                <File className="w-10 h-10 text-text-ui flex-shrink-0 mt-1" />
                <div className="flex-1 min-w-0">
                  <p className="text-text-ui font-medium truncate">{selectedFile.name}</p>
                  <div className="flex items-center space-x-3 mt-1">
                    <p className="text-sm text-muted-ui">{formatFileSize(selectedFile.size)}</p>
                    <span className="bg-surface-ui border border-border-ui rounded px-2 py-1 text-xs text-muted-ui">
                      {FILE_TYPE_LABELS[selectedFile.type] || selectedFile.type}
                    </span>
                  </div>
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleRemoveFile}
                className="ml-2 flex-shrink-0"
                aria-label="Remove file"
              >
                <X className="w-4 h-4" />
              </Button>
            </div>

            <Button onClick={handleUpload} className="w-full">
              Upload File
            </Button>
          </motion.div>
        )}

        {isUploading && (
          <motion.div
            key="uploading"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="space-y-4"
          >
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-ui">Uploading...</span>
                <span className="text-text-ui font-medium">{uploadProgress}%</span>
              </div>
              <div className="bg-surface-ui border border-border-ui rounded-full h-2 overflow-hidden">
                <motion.div
                  className="bg-black-ui h-full"
                  initial={{ width: 0 }}
                  animate={{ width: `${uploadProgress}%` }}
                  transition={{ duration: 0.3 }}
                />
              </div>
            </div>
          </motion.div>
        )}

        {uploadComplete && (
          <motion.div
            key="complete"
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="flex flex-col items-center justify-center space-y-4 py-8"
          >
            <CheckCircle className="w-12 h-12 text-text-ui" />
            <p className="text-lg font-semibold text-text-ui">Upload complete!</p>
            <Button onClick={handleRemoveFile} variant="outline">
              Upload Another
            </Button>
          </motion.div>
        )}
      </AnimatePresence>

      {validationError && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ 
            opacity: 1,
            x: [0, -10, 10, -10, 10, 0]
          }}
          transition={{ 
            opacity: { duration: 0.3 },
            x: { duration: 0.5 }
          }}
          className="flex items-start space-x-2 mt-4 p-3 bg-black-ui/30 border border-border-ui rounded-lg"
        >
          <AlertCircle className="w-5 h-5 text-muted-ui flex-shrink-0 mt-0.5" />
          <p className="text-sm text-muted-ui">{validationError.message}</p>
        </motion.div>
      )}
    </Card>
  );
}
