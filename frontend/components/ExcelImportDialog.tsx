'use client'

import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import axios from 'axios'
import { API_URL } from '../config/api'

interface ExcelImportDialogProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

interface ValidationError {
  row: number
  column: string
  message: string
  severity: 'error' | 'warning'
}

interface ValidationResult {
  valid: boolean
  errors: ValidationError[]
  preview_rows: Array<Record<string, any>>
}

interface ImportResult {
  success: boolean
  books_processed?: number
  books_matched?: number
  books_updated?: number
  articles_processed?: number
  articles_matched?: number
  documents_updated?: number
  authors_created: number
  authors_updated: number
  errors: ValidationError[]
  processing_time: number
}

type FileType = 'book' | 'article'
type ImportStep = 'upload' | 'validate' | 'preview' | 'import' | 'results'

export default function ExcelImportDialog({
  isOpen,
  onClose,
  onSuccess
}: ExcelImportDialogProps) {
  const [currentStep, setCurrentStep] = useState<ImportStep>('upload')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [fileType, setFileType] = useState<FileType>('book')
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null)
  const [importResult, setImportResult] = useState<ImportResult | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string>('')

  const resetDialog = () => {
    setCurrentStep('upload')
    setSelectedFile(null)
    setFileType('book')
    setValidationResult(null)
    setImportResult(null)
    setIsLoading(false)
    setError('')
  }

  const handleClose = () => {
    if (!isLoading) {
      resetDialog()
      onClose()
    }
  }

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const file = acceptedFiles[0]
    if (!file) return

    // Validate file extension
    if (!file.name.toLowerCase().endsWith('.xlsm')) {
      setError('Please select a .xlsm file')
      return
    }

    // Validate file size (100MB limit)
    const maxSize = 100 * 1024 * 1024
    if (file.size > maxSize) {
      setError(`File size (${(file.size / 1024 / 1024).toFixed(2)}MB) exceeds 100MB limit`)
      return
    }

    setSelectedFile(file)
    setError('')
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/vnd.ms-excel.sheet.macroEnabled.12': ['.xlsm'],
    },
    maxFiles: 1,
    disabled: isLoading,
  })

  const handleValidate = async () => {
    if (!selectedFile) return

    setIsLoading(true)
    setError('')
    setCurrentStep('validate')

    try {
      const formData = new FormData()
      formData.append('file', selectedFile)
      formData.append('file_type', fileType)

      const response = await axios.post(`${API_URL}/api/excel/validate`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })

      setValidationResult(response.data)
      setCurrentStep('preview')
    } catch (err: any) {
      console.error('Validation error:', err)
      setError(err.response?.data?.detail || 'Failed to validate Excel file')
      setCurrentStep('upload')
    } finally {
      setIsLoading(false)
    }
  }

  const handleImport = async () => {
    if (!selectedFile || !validationResult?.valid) return

    setIsLoading(true)
    setError('')
    setCurrentStep('import')

    try {
      const formData = new FormData()
      formData.append('file', selectedFile)

      const endpoint = fileType === 'book' 
        ? `${API_URL}/api/excel/import/books`
        : `${API_URL}/api/excel/import/articles`

      const response = await axios.post(endpoint, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })

      setImportResult(response.data)
      setCurrentStep('results')
      
      if (response.data.success) {
        onSuccess()
      }
    } catch (err: any) {
      console.error('Import error:', err)
      setError(err.response?.data?.detail || 'Failed to import Excel file')
      setCurrentStep('preview')
    } finally {
      setIsLoading(false)
    }
  }

  const getStepIcon = (step: ImportStep) => {
    const isActive = currentStep === step
    const isCompleted = ['upload', 'validate', 'preview', 'import', 'results'].indexOf(currentStep) > 
                       ['upload', 'validate', 'preview', 'import', 'results'].indexOf(step)

    if (isCompleted) {
      return (
        <div className="w-6 h-6 bg-mc-green rounded-full flex items-center justify-center">
          <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
      )
    }

    if (isActive) {
      return (
        <div className="w-6 h-6 bg-mc-blue rounded-full flex items-center justify-center">
          <div className="w-2 h-2 bg-white rounded-full"></div>
        </div>
      )
    }

    return (
      <div className="w-6 h-6 border-2 border-mc-gray rounded-full"></div>
    )
  }

  const renderUploadStep = () => (
    <div className="space-y-6">
      {/* File Type Selection */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-3">
          Select Import Type
        </label>
        <div className="flex gap-4">
          <label className="flex items-center">
            <input
              type="radio"
              name="fileType"
              value="book"
              checked={fileType === 'book'}
              onChange={(e) => setFileType(e.target.value as FileType)}
              disabled={isLoading}
              className="mr-2 text-mc-blue focus:ring-mc-blue"
            />
            <span className="text-sm text-gray-700">Book Metadata</span>
          </label>
          <label className="flex items-center">
            <input
              type="radio"
              name="fileType"
              value="article"
              checked={fileType === 'article'}
              onChange={(e) => setFileType(e.target.value as FileType)}
              disabled={isLoading}
              className="mr-2 text-mc-blue focus:ring-mc-blue"
            />
            <span className="text-sm text-gray-700">Article Metadata</span>
          </label>
        </div>
        <p className="text-xs text-gray-500 mt-1">
          {fileType === 'book' 
            ? 'Import book purchase URLs and author information from book-metadata.xlsm'
            : 'Import article metadata and author information from article-links.xlsm'
          }
        </p>
      </div>

      {/* File Upload */}
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-all ${
          isDragActive 
            ? 'border-mc-blue bg-blue-50' 
            : selectedFile
            ? 'border-mc-green bg-green-50'
            : 'border-gray-300 hover:border-gray-400 hover:bg-gray-50'
        } ${isLoading ? 'opacity-75 cursor-not-allowed' : ''}`}
      >
        <input {...getInputProps()} />
        
        <div className="flex flex-col items-center gap-3">
          {selectedFile ? (
            <>
              <svg className="w-12 h-12 text-mc-green" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div>
                <p className="text-mc-green font-medium">{selectedFile.name}</p>
                <p className="text-sm text-gray-500">
                  {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
            </>
          ) : isDragActive ? (
            <>
              <svg className="w-12 h-12 text-mc-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <p className="text-mc-blue font-medium">Drop the Excel file here...</p>
            </>
          ) : (
            <>
              <svg className="w-12 h-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <div>
                <p className="text-gray-600 font-medium">Drag & drop Excel file here</p>
                <p className="text-sm text-gray-500 mt-1">or click to select</p>
                <p className="text-xs text-gray-400 mt-2">Only .xlsm files, max 100MB</p>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Expected Format Info */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h4 className="text-sm font-semibold text-blue-800 mb-2">
          Expected Format
        </h4>
        {fileType === 'book' ? (
          <div className="text-sm text-blue-700">
            <p className="mb-1">Book metadata file should contain:</p>
            <ul className="list-disc list-inside space-y-1 ml-2">
              <li>URL column: MC Press purchase links</li>
              <li>Title column: Book titles for matching</li>
              <li>Author column: Author names (comma or "and" separated)</li>
            </ul>
          </div>
        ) : (
          <div className="text-sm text-blue-700">
            <p className="mb-1">Article metadata file should contain:</p>
            <ul className="list-disc list-inside space-y-1 ml-2">
              <li>export_subset sheet with feature articles</li>
              <li>Column A: Article IDs for PDF matching</li>
              <li>Column H: "yes" for feature articles</li>
              <li>Column J: Author names</li>
              <li>Column K: Article URLs</li>
              <li>Column L: Author website URLs</li>
            </ul>
          </div>
        )}
      </div>
    </div>
  )

  const renderValidationStep = () => (
    <div className="flex flex-col items-center justify-center py-12">
      <div className="w-16 h-16 border-4 border-mc-blue border-t-transparent rounded-full animate-spin mb-4"></div>
      <p className="text-lg font-medium text-gray-800">Validating Excel file...</p>
      <p className="text-sm text-gray-600 mt-1">Checking format and data integrity</p>
    </div>
  )

  const renderPreviewStep = () => {
    if (!validationResult) return null

    const errorCount = validationResult.errors.filter(e => e.severity === 'error').length
    const warningCount = validationResult.errors.filter(e => e.severity === 'warning').length

    return (
      <div className="space-y-6">
        {/* Validation Status */}
        <div className={`p-4 rounded-lg border ${
          validationResult.valid 
            ? 'bg-green-50 border-green-200' 
            : 'bg-red-50 border-red-200'
        }`}>
          <div className="flex items-center gap-2 mb-2">
            {validationResult.valid ? (
              <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            ) : (
              <svg className="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            )}
            <h4 className={`font-semibold ${
              validationResult.valid ? 'text-green-800' : 'text-red-800'
            }`}>
              {validationResult.valid ? 'Validation Passed' : 'Validation Failed'}
            </h4>
          </div>
          
          {(errorCount > 0 || warningCount > 0) && (
            <div className="flex gap-4 text-sm">
              {errorCount > 0 && (
                <span className="text-red-600">
                  {errorCount} error{errorCount !== 1 ? 's' : ''}
                </span>
              )}
              {warningCount > 0 && (
                <span className="text-yellow-600">
                  {warningCount} warning{warningCount !== 1 ? 's' : ''}
                </span>
              )}
            </div>
          )}
        </div>

        {/* Data Preview */}
        {validationResult.preview_rows.length > 0 && (
          <div>
            <h4 className="font-semibold text-gray-800 mb-3">Data Preview (First 10 rows)</h4>
            <div className="border border-gray-200 rounded-lg overflow-hidden">
              <div className="overflow-x-auto max-h-64">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                        Row
                      </th>
                      {Object.keys(validationResult.preview_rows[0] || {}).map((key) => (
                        <th key={key} className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                          {key}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {validationResult.preview_rows.map((row, index) => (
                      <tr key={index} className="hover:bg-gray-50">
                        <td className="px-3 py-2 text-sm text-gray-500">
                          {index + 1}
                        </td>
                        {Object.entries(row).map(([key, value]) => (
                          <td key={key} className="px-3 py-2 text-sm text-gray-900 max-w-xs truncate">
                            {String(value || '')}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Validation Errors */}
        {validationResult.errors.length > 0 && (
          <div>
            <h4 className="font-semibold text-gray-800 mb-3">Validation Issues</h4>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {validationResult.errors.map((error, index) => (
                <div
                  key={index}
                  className={`p-3 rounded-lg border text-sm ${
                    error.severity === 'error'
                      ? 'bg-red-50 border-red-200 text-red-800'
                      : 'bg-yellow-50 border-yellow-200 text-yellow-800'
                  }`}
                >
                  <div className="flex items-start gap-2">
                    <span className="font-medium">
                      Row {error.row}, Column {error.column}:
                    </span>
                    <span>{error.message}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    )
  }

  const renderImportStep = () => (
    <div className="flex flex-col items-center justify-center py-12">
      <div className="w-16 h-16 border-4 border-mc-orange border-t-transparent rounded-full animate-spin mb-4"></div>
      <p className="text-lg font-medium text-gray-800">Importing data...</p>
      <p className="text-sm text-gray-600 mt-1">Processing {fileType} metadata</p>
    </div>
  )

  const renderResultsStep = () => {
    if (!importResult) return null

    return (
      <div className="space-y-6">
        {/* Import Status */}
        <div className={`p-4 rounded-lg border ${
          importResult.success 
            ? 'bg-green-50 border-green-200' 
            : 'bg-red-50 border-red-200'
        }`}>
          <div className="flex items-center gap-2 mb-2">
            {importResult.success ? (
              <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            ) : (
              <svg className="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            )}
            <h4 className={`font-semibold ${
              importResult.success ? 'text-green-800' : 'text-red-800'
            }`}>
              {importResult.success ? 'Import Completed Successfully' : 'Import Failed'}
            </h4>
          </div>
        </div>

        {/* Import Statistics */}
        {importResult.success && (
          <div className="grid grid-cols-2 gap-4">
            {fileType === 'book' ? (
              <>
                <div className="bg-blue-50 p-4 rounded-lg">
                  <p className="text-2xl font-bold text-blue-600">
                    {importResult.books_processed || 0}
                  </p>
                  <p className="text-sm text-blue-800">Books Processed</p>
                </div>
                <div className="bg-green-50 p-4 rounded-lg">
                  <p className="text-2xl font-bold text-green-600">
                    {importResult.books_matched || 0}
                  </p>
                  <p className="text-sm text-green-800">Books Matched</p>
                </div>
                <div className="bg-purple-50 p-4 rounded-lg">
                  <p className="text-2xl font-bold text-purple-600">
                    {importResult.books_updated || 0}
                  </p>
                  <p className="text-sm text-purple-800">Books Updated</p>
                </div>
              </>
            ) : (
              <>
                <div className="bg-blue-50 p-4 rounded-lg">
                  <p className="text-2xl font-bold text-blue-600">
                    {importResult.articles_processed || 0}
                  </p>
                  <p className="text-sm text-blue-800">Articles Processed</p>
                </div>
                <div className="bg-green-50 p-4 rounded-lg">
                  <p className="text-2xl font-bold text-green-600">
                    {importResult.articles_matched || 0}
                  </p>
                  <p className="text-sm text-green-800">Articles Matched</p>
                </div>
                <div className="bg-purple-50 p-4 rounded-lg">
                  <p className="text-2xl font-bold text-purple-600">
                    {importResult.documents_updated || 0}
                  </p>
                  <p className="text-sm text-purple-800">Documents Updated</p>
                </div>
              </>
            )}
            <div className="bg-orange-50 p-4 rounded-lg">
              <p className="text-2xl font-bold text-orange-600">
                {importResult.authors_created}
              </p>
              <p className="text-sm text-orange-800">Authors Created</p>
            </div>
          </div>
        )}

        {/* Processing Time */}
        <div className="text-center text-sm text-gray-600">
          Processing completed in {importResult.processing_time.toFixed(2)} seconds
        </div>

        {/* Import Errors */}
        {importResult.errors.length > 0 && (
          <div>
            <h4 className="font-semibold text-gray-800 mb-3">Import Issues</h4>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {importResult.errors.map((error, index) => (
                <div
                  key={index}
                  className={`p-3 rounded-lg border text-sm ${
                    error.severity === 'error'
                      ? 'bg-red-50 border-red-200 text-red-800'
                      : 'bg-yellow-50 border-yellow-200 text-yellow-800'
                  }`}
                >
                  <div className="flex items-start gap-2">
                    <span className="font-medium">
                      Row {error.row}, Column {error.column}:
                    </span>
                    <span>{error.message}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    )
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="relative bg-white rounded-lg shadow-xl w-full max-w-4xl mx-4 max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-mc-blue rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <div>
              <h2 className="text-xl font-semibold text-gray-800">Excel Import</h2>
              <p className="text-sm text-gray-600">Import {fileType} metadata from Excel files</p>
            </div>
          </div>
          <button
            onClick={handleClose}
            disabled={isLoading}
            className="text-gray-400 hover:text-gray-600 disabled:opacity-50"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Progress Steps */}
        <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
          <div className="flex items-center justify-between">
            {[
              { key: 'upload', label: 'Upload' },
              { key: 'validate', label: 'Validate' },
              { key: 'preview', label: 'Preview' },
              { key: 'import', label: 'Import' },
              { key: 'results', label: 'Results' }
            ].map((step, index) => (
              <div key={step.key} className="flex items-center">
                <div className="flex items-center gap-2">
                  {getStepIcon(step.key as ImportStep)}
                  <span className={`text-sm font-medium ${
                    currentStep === step.key ? 'text-mc-blue' : 'text-gray-500'
                  }`}>
                    {step.label}
                  </span>
                </div>
                {index < 4 && (
                  <div className="w-8 h-px bg-gray-300 mx-4"></div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[60vh]">
          {currentStep === 'upload' && renderUploadStep()}
          {currentStep === 'validate' && renderValidationStep()}
          {currentStep === 'preview' && renderPreviewStep()}
          {currentStep === 'import' && renderImportStep()}
          {currentStep === 'results' && renderResultsStep()}

          {/* Error Message */}
          {error && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-center gap-2">
                <svg className="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div>
                  <h4 className="text-sm font-semibold text-red-800">Error</h4>
                  <p className="text-sm text-red-700 mt-1">{error}</p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex gap-3 justify-end p-6 border-t border-gray-200 bg-gray-50">
          {currentStep === 'upload' && (
            <>
              <button
                onClick={handleClose}
                disabled={isLoading}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Cancel
              </button>
              <button
                onClick={handleValidate}
                disabled={!selectedFile || isLoading}
                className="px-4 py-2 text-sm font-medium text-white bg-mc-blue rounded-lg hover:bg-mc-blue-dark disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {isLoading && (
                  <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="m4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                )}
                Validate File
              </button>
            </>
          )}

          {currentStep === 'preview' && (
            <>
              <button
                onClick={() => setCurrentStep('upload')}
                disabled={isLoading}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Back
              </button>
              <button
                onClick={handleImport}
                disabled={!validationResult?.valid || isLoading}
                className="px-4 py-2 text-sm font-medium text-white bg-mc-orange rounded-lg hover:bg-mc-orange-dark disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {isLoading && (
                  <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="m4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                )}
                Import Data
              </button>
            </>
          )}

          {currentStep === 'results' && (
            <>
              <button
                onClick={resetDialog}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Import Another File
              </button>
              <button
                onClick={handleClose}
                className="px-4 py-2 text-sm font-medium text-white bg-mc-green rounded-lg hover:bg-mc-green-dark"
              >
                Done
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}