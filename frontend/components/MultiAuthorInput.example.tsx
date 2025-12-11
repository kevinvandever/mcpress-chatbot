'use client'

import { useState } from 'react'
import MultiAuthorInput from './MultiAuthorInput'

// Example usage of MultiAuthorInput component
export default function MultiAuthorInputExample() {
  const [authors, setAuthors] = useState([
    {
      id: 1,
      name: 'John Doe',
      site_url: 'https://johndoe.com',
      order: 0
    },
    {
      name: 'Jane Smith', // New author without ID
      site_url: 'https://janesmith.com',
      order: 1
    }
  ])

  const handleAuthorsChange = (newAuthors: typeof authors) => {
    console.log('Authors updated:', newAuthors)
    setAuthors(newAuthors)
  }

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 mb-2">
          MultiAuthorInput Component Example
        </h1>
        <p className="text-gray-600">
          This component provides a complete author management interface with search,
          autocomplete, drag-and-drop reordering, and inline URL editing.
        </p>
      </div>

      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Document Authors
        </h2>
        
        <MultiAuthorInput
          authors={authors}
          onChange={handleAuthorsChange}
          placeholder="Search for authors or add new ones..."
          maxAuthors={5}
          className="w-full"
        />
      </div>

      <div className="bg-gray-50 border border-gray-200 rounded-lg p-6">
        <h3 className="text-md font-semibold text-gray-900 mb-3">
          Current Authors Data:
        </h3>
        <pre className="text-sm text-gray-700 bg-white p-3 rounded border overflow-x-auto">
          {JSON.stringify(authors, null, 2)}
        </pre>
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h3 className="text-md font-semibold text-blue-900 mb-3">
          Features Demonstrated:
        </h3>
        <ul className="text-sm text-blue-800 space-y-2">
          <li>• <strong>Author Search:</strong> Type to search existing authors with autocomplete</li>
          <li>• <strong>Add New Authors:</strong> Create new authors inline when they don't exist</li>
          <li>• <strong>Drag & Drop:</strong> Reorder authors by dragging the handle icons</li>
          <li>• <strong>Arrow Buttons:</strong> Use up/down arrows to reorder authors</li>
          <li>• <strong>URL Editing:</strong> Click website links to edit author URLs inline</li>
          <li>• <strong>Validation:</strong> URL format validation and last-author protection</li>
          <li>• <strong>MC Press Styling:</strong> Uses official MC Press design tokens</li>
          <li>• <strong>Accessibility:</strong> Full keyboard navigation and screen reader support</li>
        </ul>
      </div>

      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
        <h3 className="text-md font-semibold text-yellow-900 mb-3">
          Integration Notes:
        </h3>
        <ul className="text-sm text-yellow-800 space-y-2">
          <li>• Integrates with <code>/api/authors/search</code> endpoint</li>
          <li>• Filters out authors already in the current list</li>
          <li>• Maintains author order with automatic reindexing</li>
          <li>• Supports both existing authors (with IDs) and new authors</li>
          <li>• Validates URLs must start with http:// or https://</li>
          <li>• Enforces minimum of 1 author per document</li>
        </ul>
      </div>
    </div>
  )
}

// Import the Author type from MultiAuthorInput
import type { Author } from './MultiAuthorInput'

// Example of how to use in a form context
export function DocumentEditFormExample() {
  const [formData, setFormData] = useState<{
    title: string
    document_type: 'book' | 'article'
    authors: Author[]
    mc_press_url: string
    article_url: string
  }>({
    title: 'Sample Document',
    document_type: 'book',
    authors: [
      { id: 1, name: 'John Doe', site_url: 'https://johndoe.com', order: 0 }
    ],
    mc_press_url: 'https://mcpress.com/sample-book',
    article_url: ''
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    console.log('Form submitted:', formData)
    // Here you would typically call your API to save the document
  }

  return (
    <div className="max-w-2xl mx-auto p-6">
      <h2 className="text-xl font-bold text-gray-900 mb-6">
        Document Edit Form Example
      </h2>
      
      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Document Title
          </label>
          <input
            type="text"
            value={formData.title}
            onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Document Type
          </label>
          <div className="flex gap-4">
            <label className="flex items-center">
              <input
                type="radio"
                value="book"
                checked={formData.document_type === 'book'}
                onChange={(e) => setFormData(prev => ({ ...prev, document_type: e.target.value as 'book' }))}
                className="mr-2"
              />
              Book
            </label>
            <label className="flex items-center">
              <input
                type="radio"
                value="article"
                checked={formData.document_type === 'article'}
                onChange={(e) => setFormData(prev => ({ ...prev, document_type: e.target.value as 'article' }))}
                className="mr-2"
              />
              Article
            </label>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Authors
          </label>
          <MultiAuthorInput
            authors={formData.authors}
            onChange={(authors) => setFormData(prev => ({ ...prev, authors }))}
            placeholder="Search for document authors..."
          />
        </div>

        {formData.document_type === 'book' && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              MC Press URL
            </label>
            <input
              type="url"
              value={formData.mc_press_url}
              onChange={(e) => setFormData(prev => ({ ...prev, mc_press_url: e.target.value }))}
              placeholder="https://mcpress.com/book-name"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        )}

        {formData.document_type === 'article' && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Article URL
            </label>
            <input
              type="url"
              value={formData.article_url}
              onChange={(e) => setFormData(prev => ({ ...prev, article_url: e.target.value }))}
              placeholder="https://example.com/article"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        )}

        <div className="flex gap-3">
          <button
            type="submit"
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          >
            Save Document
          </button>
          <button
            type="button"
            className="px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300 focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}