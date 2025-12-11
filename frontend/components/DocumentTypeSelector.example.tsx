import { useState } from 'react'
import DocumentTypeSelector, { DocumentType } from './DocumentTypeSelector'

// =====================================================
// Example Usage of DocumentTypeSelector Component
// =====================================================

export default function DocumentTypeSelectorExample() {
  const [documentData, setDocumentData] = useState({
    documentType: 'book' as DocumentType,
    mcPressUrl: '',
    articleUrl: ''
  })

  const handleDocumentDataChange = (data: {
    documentType: DocumentType
    mcPressUrl?: string
    articleUrl?: string
  }) => {
    setDocumentData({
      documentType: data.documentType,
      mcPressUrl: data.mcPressUrl || '',
      articleUrl: data.articleUrl || ''
    })
  }

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">
          DocumentTypeSelector Examples
        </h1>
        <p className="text-gray-600">
          Interactive examples showing different configurations of the DocumentTypeSelector component.
        </p>
      </div>

      {/* Basic Example */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">
          Basic Usage
        </h2>
        
        <DocumentTypeSelector
          documentType={documentData.documentType}
          mcPressUrl={documentData.mcPressUrl}
          articleUrl={documentData.articleUrl}
          onChange={handleDocumentDataChange}
        />

        {/* Current State Display */}
        <div className="mt-6 p-4 bg-gray-50 rounded-lg">
          <h3 className="text-sm font-medium text-gray-700 mb-2">Current State:</h3>
          <pre className="text-xs text-gray-600 whitespace-pre-wrap">
            {JSON.stringify(documentData, null, 2)}
          </pre>
        </div>
      </div>

      {/* Pre-filled Book Example */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">
          Pre-filled Book Example
        </h2>
        
        <DocumentTypeSelector
          documentType="book"
          mcPressUrl="https://mcpress.com/rpg-programming-guide"
          articleUrl=""
          onChange={(data) => console.log('Book data changed:', data)}
        />
      </div>

      {/* Pre-filled Article Example */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">
          Pre-filled Article Example
        </h2>
        
        <DocumentTypeSelector
          documentType="article"
          mcPressUrl=""
          articleUrl="https://example.com/ibm-i-modernization-guide"
          onChange={(data) => console.log('Article data changed:', data)}
        />
      </div>

      {/* Disabled Example */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">
          Disabled State
        </h2>
        
        <DocumentTypeSelector
          documentType="book"
          mcPressUrl="https://mcpress.com/sample-book"
          articleUrl=""
          onChange={(data) => console.log('Disabled data changed:', data)}
          disabled={true}
        />
      </div>

      {/* Without Labels Example */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">
          Without Labels (Compact)
        </h2>
        
        <DocumentTypeSelector
          documentType="article"
          mcPressUrl=""
          articleUrl=""
          onChange={(data) => console.log('Compact data changed:', data)}
          showLabels={false}
        />
      </div>

      {/* Custom Styling Example */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">
          Custom Styling
        </h2>
        
        <DocumentTypeSelector
          documentType="book"
          mcPressUrl=""
          articleUrl=""
          onChange={(data) => console.log('Custom styled data changed:', data)}
          className="bg-blue-50 p-4 rounded-lg border border-blue-200"
        />
      </div>

      {/* Integration Example */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">
          Form Integration Example
        </h2>
        
        <form className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Document Title
            </label>
            <input
              type="text"
              placeholder="Enter document title..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-mc-blue focus:border-mc-blue"
            />
          </div>

          <DocumentTypeSelector
            documentType={documentData.documentType}
            mcPressUrl={documentData.mcPressUrl}
            articleUrl={documentData.articleUrl}
            onChange={handleDocumentDataChange}
          />

          <div className="flex gap-3 pt-4">
            <button
              type="submit"
              className="px-4 py-2 bg-mc-blue text-white rounded-lg hover:bg-mc-blue-dark transition-colors"
            >
              Save Document
            </button>
            <button
              type="button"
              className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>

      {/* Validation Example */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">
          URL Validation Example
        </h2>
        <p className="text-sm text-gray-600 mb-4">
          Try entering invalid URLs to see validation in action:
        </p>
        
        <DocumentTypeSelector
          documentType="book"
          mcPressUrl="invalid-url-example"
          articleUrl=""
          onChange={(data) => console.log('Validation example data changed:', data)}
        />
      </div>

      {/* Usage Notes */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-blue-800 mb-4">
          Usage Notes
        </h2>
        <div className="text-sm text-blue-700 space-y-2">
          <p><strong>Document Types:</strong></p>
          <ul className="list-disc list-inside ml-4 space-y-1">
            <li><strong>Book:</strong> Shows MC Press URL field for purchase links</li>
            <li><strong>Article:</strong> Shows Article URL field for direct web links</li>
          </ul>
          
          <p className="pt-2"><strong>URL Validation:</strong></p>
          <ul className="list-disc list-inside ml-4 space-y-1">
            <li>URLs must start with http:// or https://</li>
            <li>Empty URLs are considered valid (optional)</li>
            <li>Real-time validation with error messages</li>
          </ul>
          
          <p className="pt-2"><strong>Props:</strong></p>
          <ul className="list-disc list-inside ml-4 space-y-1">
            <li><code>documentType</code>: 'book' | 'article' (required)</li>
            <li><code>mcPressUrl</code>: string (optional)</li>
            <li><code>articleUrl</code>: string (optional)</li>
            <li><code>onChange</code>: callback function (required)</li>
            <li><code>disabled</code>: boolean (optional)</li>
            <li><code>className</code>: string (optional)</li>
            <li><code>showLabels</code>: boolean (optional, default: true)</li>
          </ul>
        </div>
      </div>
    </div>
  )
}