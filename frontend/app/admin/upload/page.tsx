'use client';

import { useState, useCallback, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import AdminLayout from '@/components/AdminLayout';
import { useAuth } from '@/hooks/useAuth';
import { useRouter } from 'next/navigation';

interface BookMetadata {
  filename: string;
  title: string;
  category: string;
  subcategory?: string;
  author?: string;
  year?: number;
  tags?: string[];
  description?: string;
  mc_press_url?: string;
}

interface UploadFile {
  file: File;
  metadata: BookMetadata;
  progress: number;
  status: 'pending' | 'uploading' | 'processing' | 'completed' | 'failed';
  error?: string;
}

const CATEGORIES = {
  programming: {
    name: 'Programming Languages',
    subcategories: ['python', 'javascript', 'java', 'c++', 'rpg', 'cobol', 'sql']
  },
  systems: {
    name: 'Systems & Architecture',
    subcategories: ['ibm-i', 'as400', 'mainframe', 'unix', 'linux', 'windows']
  },
  databases: {
    name: 'Database Systems',
    subcategories: ['db2', 'sql-server', 'oracle', 'mysql', 'postgresql']
  },
  web: {
    name: 'Web Development',
    subcategories: ['frontend', 'backend', 'frameworks', 'apis']
  },
  devops: {
    name: 'DevOps & Infrastructure',
    subcategories: ['deployment', 'monitoring', 'ci-cd', 'containers']
  },
  business: {
    name: 'Business Applications',
    subcategories: ['erp', 'crm', 'accounting', 'hr']
  }
};

export default function UploadPage() {
  const [uploadFiles, setUploadFiles] = useState<UploadFile[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [selectedFileIndex, setSelectedFileIndex] = useState<number | null>(null);
  const { isAuthenticated } = useAuth();
  const router = useRouter();

  // Redirect if not authenticated
  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/admin/login');
    }
  }, [isAuthenticated, router]);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newFiles = acceptedFiles
      .filter(file => file.type === 'application/pdf')
      .slice(0, 10) // Limit to 10 files
      .map(file => ({
        file,
        metadata: {
          filename: file.name,
          title: file.name.replace('.pdf', '').replace(/_/g, ' '),
          category: 'general',
          tags: []
        },
        progress: 0,
        status: 'pending' as const
      }));

    setUploadFiles(prev => [...prev, ...newFiles]);
    if (newFiles.length > 0 && selectedFileIndex === null) {
      setSelectedFileIndex(0);
    }
  }, [selectedFileIndex]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf']
    },
    maxSize: 100 * 1024 * 1024, // 100MB
    multiple: true
  });

  const updateMetadata = (index: number, field: keyof BookMetadata, value: any) => {
    setUploadFiles(prev => {
      const updated = [...prev];
      (updated[index].metadata as any)[field] = value;
      return updated;
    });
  };

  const removeFile = (index: number) => {
    setUploadFiles(prev => prev.filter((_, i) => i !== index));
    if (selectedFileIndex === index) {
      setSelectedFileIndex(null);
    } else if (selectedFileIndex !== null && selectedFileIndex > index) {
      setSelectedFileIndex(selectedFileIndex - 1);
    }
  };

  const handleUploadFiles = async () => {
    if (uploadFiles.length === 0) return;
    
    setIsUploading(true);
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const token = typeof window !== 'undefined' ? localStorage.getItem('adminToken') : null;

    for (let i = 0; i < uploadFiles.length; i++) {
      const uploadFile = uploadFiles[i];
      
      // Update status to uploading
      setUploadFiles(prev => {
        const updated = [...prev];
        updated[i].status = 'uploading';
        return updated;
      });

      try {
        // Create FormData for file upload
        const formData = new FormData();
        formData.append('files', uploadFile.file);

        // Upload file
        const uploadResponse = await fetch(`${apiUrl}/batch-upload`, {
          method: 'POST',
          headers: token ? { 'Authorization': `Bearer ${token}` } : {},
          body: formData
        });

        if (!uploadResponse.ok) {
          throw new Error(`Upload failed: ${uploadResponse.statusText}`);
        }

        await uploadResponse.json(); // Consume response but don't store if not needed

        // Update progress
        setUploadFiles(prev => {
          const updated = [...prev];
          updated[i].progress = 50;
          updated[i].status = 'processing';
          return updated;
        });

        // Submit metadata
        const metadataResponse = await fetch(`${apiUrl}/complete-upload`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {})
          },
          body: JSON.stringify({
            filename: uploadFile.metadata.filename,
            title: uploadFile.metadata.title,
            author: uploadFile.metadata.author || 'Unknown',
            category: uploadFile.metadata.category,
            subcategory: uploadFile.metadata.subcategory,
            tags: uploadFile.metadata.tags,
            description: uploadFile.metadata.description,
            mc_press_url: uploadFile.metadata.mc_press_url,
            year: uploadFile.metadata.year
          })
        });

        if (!metadataResponse.ok) {
          // If metadata fails, still mark as completed since file is uploaded
          console.warn('Metadata submission failed:', metadataResponse.statusText);
        }

        // Mark as completed
        setUploadFiles(prev => {
          const updated = [...prev];
          updated[i].progress = 100;
          updated[i].status = 'completed';
          return updated;
        });

      } catch (error) {
        console.error(`Failed to upload ${uploadFile.file.name}:`, error);
        setUploadFiles(prev => {
          const updated = [...prev];
          updated[i].status = 'failed';
          updated[i].error = error instanceof Error ? error.message : 'Upload failed';
          return updated;
        });
      }
    }

    setIsUploading(false);
  };

  const selectedFile = selectedFileIndex !== null ? uploadFiles[selectedFileIndex] : null;

  return (
    <AdminLayout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Upload PDFs</h1>
          <p className="mt-2 text-sm text-gray-600">
            Upload and process PDF documents to add them to the chatbot knowledge base
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left Column - File Upload & List */}
          <div className="space-y-6">
            {/* Dropzone */}
            <div
              {...getRootProps()}
              className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'
              }`}
            >
              <input {...getInputProps()} />
              <svg
                className="mx-auto h-12 w-12 text-gray-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                />
              </svg>
              <p className="mt-2 text-sm text-gray-600">
                {isDragActive
                  ? 'Drop the PDFs here...'
                  : 'Drag & drop PDF files here, or click to select'}
              </p>
              <p className="mt-1 text-xs text-gray-500">
                Maximum 10 files, 100MB each
              </p>
            </div>

            {/* File List */}
            {uploadFiles.length > 0 && (
              <div className="bg-white rounded-lg shadow">
                <div className="px-4 py-3 border-b border-gray-200">
                  <h3 className="text-sm font-medium text-gray-900">
                    Files ({uploadFiles.length})
                  </h3>
                </div>
                <ul className="divide-y divide-gray-200 max-h-96 overflow-y-auto">
                  {uploadFiles.map((file, index) => (
                    <li
                      key={index}
                      className={`px-4 py-3 hover:bg-gray-50 cursor-pointer ${
                        selectedFileIndex === index ? 'bg-blue-50' : ''
                      }`}
                      onClick={() => setSelectedFileIndex(index)}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-900 truncate">
                            {file.metadata.title || file.file.name}
                          </p>
                          <p className="text-xs text-gray-500">
                            {(file.file.size / 1024 / 1024).toFixed(2)} MB
                          </p>
                        </div>
                        <div className="flex items-center space-x-2">
                          {file.status === 'pending' && (
                            <span className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded">
                              Pending
                            </span>
                          )}
                          {file.status === 'uploading' && (
                            <span className="px-2 py-1 text-xs bg-blue-100 text-blue-600 rounded">
                              Uploading...
                            </span>
                          )}
                          {file.status === 'processing' && (
                            <span className="px-2 py-1 text-xs bg-yellow-100 text-yellow-600 rounded">
                              Processing...
                            </span>
                          )}
                          {file.status === 'completed' && (
                            <span className="px-2 py-1 text-xs bg-green-100 text-green-600 rounded">
                              Complete
                            </span>
                          )}
                          {file.status === 'failed' && (
                            <span className="px-2 py-1 text-xs bg-red-100 text-red-600 rounded">
                              Failed
                            </span>
                          )}
                          {file.status === 'pending' && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                removeFile(index);
                              }}
                              className="text-red-500 hover:text-red-700"
                            >
                              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                              </svg>
                            </button>
                          )}
                        </div>
                      </div>
                      {file.progress > 0 && file.progress < 100 && (
                        <div className="mt-2 w-full bg-gray-200 rounded-full h-1">
                          <div
                            className="bg-blue-600 h-1 rounded-full transition-all duration-300"
                            style={{ width: `${file.progress}%` }}
                          />
                        </div>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Upload Button */}
            {uploadFiles.length > 0 && (
              <button
                onClick={handleUploadFiles}
                disabled={isUploading || uploadFiles.every(f => f.status !== 'pending')}
                className={`w-full px-4 py-2 text-sm font-medium rounded-md ${
                  isUploading || uploadFiles.every(f => f.status !== 'pending')
                    ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                    : 'bg-blue-600 text-white hover:bg-blue-700'
                }`}
              >
                {isUploading ? 'Uploading...' : 'Upload All Files'}
              </button>
            )}
          </div>

          {/* Right Column - Metadata Form */}
          <div>
            {selectedFile ? (
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">
                  Metadata for: {selectedFile.file.name}
                </h3>
                <form className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      Title *
                    </label>
                    <input
                      type="text"
                      value={selectedFile.metadata.title}
                      onChange={(e) => updateMetadata(selectedFileIndex!, 'title', e.target.value)}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                      disabled={selectedFile.status !== 'pending'}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      Author
                    </label>
                    <input
                      type="text"
                      value={selectedFile.metadata.author || ''}
                      onChange={(e) => updateMetadata(selectedFileIndex!, 'author', e.target.value)}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                      disabled={selectedFile.status !== 'pending'}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      Category *
                    </label>
                    <select
                      value={selectedFile.metadata.category}
                      onChange={(e) => {
                        updateMetadata(selectedFileIndex!, 'category', e.target.value);
                        updateMetadata(selectedFileIndex!, 'subcategory', undefined);
                      }}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                      disabled={selectedFile.status !== 'pending'}
                    >
                      <option value="general">General</option>
                      {Object.entries(CATEGORIES).map(([key, cat]) => (
                        <option key={key} value={key}>
                          {cat.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  {selectedFile.metadata.category !== 'general' && 
                   CATEGORIES[selectedFile.metadata.category as keyof typeof CATEGORIES] && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700">
                        Subcategory
                      </label>
                      <select
                        value={selectedFile.metadata.subcategory || ''}
                        onChange={(e) => updateMetadata(selectedFileIndex!, 'subcategory', e.target.value)}
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                        disabled={selectedFile.status !== 'pending'}
                      >
                        <option value="">Select subcategory...</option>
                        {CATEGORIES[selectedFile.metadata.category as keyof typeof CATEGORIES].subcategories.map(sub => (
                          <option key={sub} value={sub}>
                            {sub.charAt(0).toUpperCase() + sub.slice(1).replace(/-/g, ' ')}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}

                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      Year
                    </label>
                    <input
                      type="number"
                      value={selectedFile.metadata.year || ''}
                      onChange={(e) => updateMetadata(selectedFileIndex!, 'year', parseInt(e.target.value) || undefined)}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                      disabled={selectedFile.status !== 'pending'}
                      min="1900"
                      max={new Date().getFullYear()}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      MC Press URL
                    </label>
                    <input
                      type="url"
                      value={selectedFile.metadata.mc_press_url || ''}
                      onChange={(e) => updateMetadata(selectedFileIndex!, 'mc_press_url', e.target.value)}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                      disabled={selectedFile.status !== 'pending'}
                      placeholder="https://mc-press.com/..."
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      Tags (comma-separated)
                    </label>
                    <input
                      type="text"
                      value={selectedFile.metadata.tags?.join(', ') || ''}
                      onChange={(e) => updateMetadata(
                        selectedFileIndex!, 
                        'tags', 
                        e.target.value.split(',').map(t => t.trim()).filter(Boolean)
                      )}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                      disabled={selectedFile.status !== 'pending'}
                      placeholder="ibm, rpg, programming"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      Description
                    </label>
                    <textarea
                      value={selectedFile.metadata.description || ''}
                      onChange={(e) => updateMetadata(selectedFileIndex!, 'description', e.target.value)}
                      rows={3}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                      disabled={selectedFile.status !== 'pending'}
                    />
                  </div>
                </form>

                {selectedFile.status === 'failed' && selectedFile.error && (
                  <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
                    <p className="text-sm text-red-600">
                      Error: {selectedFile.error}
                    </p>
                  </div>
                )}
              </div>
            ) : (
              <div className="bg-gray-50 rounded-lg p-8 text-center">
                <svg
                  className="mx-auto h-12 w-12 text-gray-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
                <p className="mt-2 text-sm text-gray-600">
                  Select a file to edit its metadata
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </AdminLayout>
  );
}