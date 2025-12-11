import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import DocumentTypeSelector, { DocumentType } from './DocumentTypeSelector'

// Mock data for testing
const mockOnChange = jest.fn()

const defaultProps = {
  documentType: 'book' as DocumentType,
  mcPressUrl: '',
  articleUrl: '',
  onChange: mockOnChange,
}

describe('DocumentTypeSelector', () => {
  beforeEach(() => {
    mockOnChange.mockClear()
  })

  describe('Document Type Selection', () => {
    it('renders both book and article options', () => {
      render(<DocumentTypeSelector {...defaultProps} />)
      
      expect(screen.getByText('Book')).toBeInTheDocument()
      expect(screen.getByText('Article')).toBeInTheDocument()
      expect(screen.getByText('Published book with purchase link')).toBeInTheDocument()
      expect(screen.getByText('Online article with direct link')).toBeInTheDocument()
    })

    it('shows book as selected by default', () => {
      render(<DocumentTypeSelector {...defaultProps} />)
      
      const bookRadio = screen.getByRole('radio', { name: /book/i })
      const articleRadio = screen.getByRole('radio', { name: /article/i })
      
      expect(bookRadio).toBeChecked()
      expect(articleRadio).not.toBeChecked()
    })

    it('switches to article when clicked', () => {
      render(<DocumentTypeSelector {...defaultProps} />)
      
      const articleRadio = screen.getByRole('radio', { name: /article/i })
      fireEvent.click(articleRadio)
      
      expect(mockOnChange).toHaveBeenCalledWith({
        documentType: 'article',
        mcPressUrl: undefined,
        articleUrl: ''
      })
    })

    it('switches to book when clicked', () => {
      render(<DocumentTypeSelector {...defaultProps} documentType="article" />)
      
      const bookRadio = screen.getByRole('radio', { name: /book/i })
      fireEvent.click(bookRadio)
      
      expect(mockOnChange).toHaveBeenCalledWith({
        documentType: 'book',
        mcPressUrl: '',
        articleUrl: undefined
      })
    })
  })

  describe('URL Fields', () => {
    it('shows MC Press URL field when book is selected', () => {
      render(<DocumentTypeSelector {...defaultProps} documentType="book" />)
      
      expect(screen.getByLabelText(/MC Press Purchase URL/i)).toBeInTheDocument()
      expect(screen.getByPlaceholderText('https://mcpress.com/book-title')).toBeInTheDocument()
      expect(screen.queryByLabelText(/Article URL/i)).not.toBeInTheDocument()
    })

    it('shows Article URL field when article is selected', () => {
      render(<DocumentTypeSelector {...defaultProps} documentType="article" />)
      
      expect(screen.getByLabelText(/Article URL/i)).toBeInTheDocument()
      expect(screen.getByPlaceholderText('https://example.com/article-title')).toBeInTheDocument()
      expect(screen.queryByLabelText(/MC Press Purchase URL/i)).not.toBeInTheDocument()
    })

    it('updates MC Press URL when typing', () => {
      render(<DocumentTypeSelector {...defaultProps} documentType="book" />)
      
      const urlInput = screen.getByLabelText(/MC Press Purchase URL/i)
      fireEvent.change(urlInput, { target: { value: 'https://mcpress.com/test-book' } })
      
      expect(mockOnChange).toHaveBeenCalledWith({
        documentType: 'book',
        mcPressUrl: 'https://mcpress.com/test-book',
        articleUrl: undefined
      })
    })

    it('updates Article URL when typing', () => {
      render(<DocumentTypeSelector {...defaultProps} documentType="article" />)
      
      const urlInput = screen.getByLabelText(/Article URL/i)
      fireEvent.change(urlInput, { target: { value: 'https://example.com/test-article' } })
      
      expect(mockOnChange).toHaveBeenCalledWith({
        documentType: 'article',
        mcPressUrl: undefined,
        articleUrl: 'https://example.com/test-article'
      })
    })
  })

  describe('URL Validation', () => {
    it('shows error for invalid MC Press URL', async () => {
      render(<DocumentTypeSelector {...defaultProps} documentType="book" />)
      
      const urlInput = screen.getByLabelText(/MC Press Purchase URL/i)
      fireEvent.change(urlInput, { target: { value: 'invalid-url' } })
      
      await waitFor(() => {
        expect(screen.getByText(/Please enter a valid URL/i)).toBeInTheDocument()
      })
    })

    it('shows error for invalid Article URL', async () => {
      render(<DocumentTypeSelector {...defaultProps} documentType="article" />)
      
      const urlInput = screen.getByLabelText(/Article URL/i)
      fireEvent.change(urlInput, { target: { value: 'not-a-url' } })
      
      await waitFor(() => {
        expect(screen.getByText(/Please enter a valid URL/i)).toBeInTheDocument()
      })
    })

    it('accepts valid HTTP URLs', () => {
      render(<DocumentTypeSelector {...defaultProps} documentType="book" />)
      
      const urlInput = screen.getByLabelText(/MC Press Purchase URL/i)
      fireEvent.change(urlInput, { target: { value: 'http://mcpress.com/book' } })
      
      expect(screen.queryByText(/Please enter a valid URL/i)).not.toBeInTheDocument()
    })

    it('accepts valid HTTPS URLs', () => {
      render(<DocumentTypeSelector {...defaultProps} documentType="book" />)
      
      const urlInput = screen.getByLabelText(/MC Press Purchase URL/i)
      fireEvent.change(urlInput, { target: { value: 'https://mcpress.com/book' } })
      
      expect(screen.queryByText(/Please enter a valid URL/i)).not.toBeInTheDocument()
    })

    it('accepts empty URLs', () => {
      render(<DocumentTypeSelector {...defaultProps} documentType="book" />)
      
      const urlInput = screen.getByLabelText(/MC Press Purchase URL/i)
      fireEvent.change(urlInput, { target: { value: '' } })
      
      expect(screen.queryByText(/Please enter a valid URL/i)).not.toBeInTheDocument()
    })
  })

  describe('Disabled State', () => {
    it('disables radio buttons when disabled prop is true', () => {
      render(<DocumentTypeSelector {...defaultProps} disabled={true} />)
      
      const bookRadio = screen.getByRole('radio', { name: /book/i })
      const articleRadio = screen.getByRole('radio', { name: /article/i })
      
      expect(bookRadio).toBeDisabled()
      expect(articleRadio).toBeDisabled()
    })

    it('disables URL input when disabled prop is true', () => {
      render(<DocumentTypeSelector {...defaultProps} documentType="book" disabled={true} />)
      
      const urlInput = screen.getByLabelText(/MC Press Purchase URL/i)
      expect(urlInput).toBeDisabled()
    })

    it('does not call onChange when disabled', () => {
      render(<DocumentTypeSelector {...defaultProps} disabled={true} />)
      
      const articleRadio = screen.getByRole('radio', { name: /article/i })
      fireEvent.click(articleRadio)
      
      expect(mockOnChange).not.toHaveBeenCalled()
    })
  })

  describe('Props Synchronization', () => {
    it('updates local state when mcPressUrl prop changes', () => {
      const { rerender } = render(<DocumentTypeSelector {...defaultProps} documentType="book" mcPressUrl="" />)
      
      rerender(<DocumentTypeSelector {...defaultProps} documentType="book" mcPressUrl="https://mcpress.com/new-book" />)
      
      const urlInput = screen.getByLabelText(/MC Press Purchase URL/i) as HTMLInputElement
      expect(urlInput.value).toBe('https://mcpress.com/new-book')
    })

    it('updates local state when articleUrl prop changes', () => {
      const { rerender } = render(<DocumentTypeSelector {...defaultProps} documentType="article" articleUrl="" />)
      
      rerender(<DocumentTypeSelector {...defaultProps} documentType="article" articleUrl="https://example.com/new-article" />)
      
      const urlInput = screen.getByLabelText(/Article URL/i) as HTMLInputElement
      expect(urlInput.value).toBe('https://example.com/new-article')
    })
  })

  describe('Help Text', () => {
    it('shows help text explaining document types', () => {
      render(<DocumentTypeSelector {...defaultProps} />)
      
      expect(screen.getByText(/Books:/)).toBeInTheDocument()
      expect(screen.getByText(/Articles:/)).toBeInTheDocument()
      expect(screen.getByText(/URLs must start with http/)).toBeInTheDocument()
    })
  })

  describe('Labels', () => {
    it('shows labels by default', () => {
      render(<DocumentTypeSelector {...defaultProps} />)
      
      expect(screen.getByText('Document Type')).toBeInTheDocument()
    })

    it('hides labels when showLabels is false', () => {
      render(<DocumentTypeSelector {...defaultProps} showLabels={false} />)
      
      expect(screen.queryByText('Document Type')).not.toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('has proper ARIA labels for radio buttons', () => {
      render(<DocumentTypeSelector {...defaultProps} />)
      
      const bookRadio = screen.getByRole('radio', { name: /book/i })
      const articleRadio = screen.getByRole('radio', { name: /article/i })
      
      expect(bookRadio).toHaveAttribute('value', 'book')
      expect(articleRadio).toHaveAttribute('value', 'article')
    })

    it('has proper labels for URL inputs', () => {
      render(<DocumentTypeSelector {...defaultProps} documentType="book" />)
      
      const urlInput = screen.getByLabelText(/MC Press Purchase URL/i)
      expect(urlInput).toHaveAttribute('type', 'url')
    })

    it('associates error messages with inputs', async () => {
      render(<DocumentTypeSelector {...defaultProps} documentType="book" />)
      
      const urlInput = screen.getByLabelText(/MC Press Purchase URL/i)
      fireEvent.change(urlInput, { target: { value: 'invalid-url' } })
      
      await waitFor(() => {
        const errorMessage = screen.getByText(/Please enter a valid URL/i)
        expect(errorMessage).toBeInTheDocument()
      })
    })
  })
})