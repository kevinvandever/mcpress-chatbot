import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import CompactSources from '../CompactSources'

describe('CompactSources - Multi-Author Button Behavior', () => {
  it('shows "Author" (singular) button as direct link when only one author has a website', () => {
    const sources = [
      {
        filename: 'test-book.pdf',
        page: 1,
        title: 'Test Book',
        authors: [
          { id: 1, name: 'John Doe', site_url: 'https://johndoe.com', order: 0 }
        ]
      }
    ]

    render(<CompactSources sources={sources} />)
    
    // Should show "Author" (singular)
    const authorButton = screen.getByText('Author')
    expect(authorButton).toBeInTheDocument()
    expect(authorButton.tagName).toBe('A') // Should be a link, not a button
    expect(authorButton).toHaveAttribute('href', 'https://johndoe.com')
  })

  it('shows "Author" (singular) when multiple authors but only one has a website', () => {
    const sources = [
      {
        filename: 'test-book.pdf',
        page: 1,
        title: 'Test Book',
        authors: [
          { id: 1, name: 'John Doe', site_url: 'https://johndoe.com', order: 0 },
          { id: 2, name: 'Jane Smith', site_url: null, order: 1 }
        ]
      }
    ]

    render(<CompactSources sources={sources} />)
    
    // Should show "Author" (singular) because only one has a website
    const authorButton = screen.getByText('Author')
    expect(authorButton).toBeInTheDocument()
    expect(authorButton.tagName).toBe('A')
    expect(authorButton).toHaveAttribute('href', 'https://johndoe.com')
  })

  it('shows "Authors" (plural) button with dropdown when multiple authors have websites', () => {
    const sources = [
      {
        filename: 'test-book.pdf',
        page: 1,
        title: 'Test Book',
        authors: [
          { id: 1, name: 'John Doe', site_url: 'https://johndoe.com', order: 0 },
          { id: 2, name: 'Jane Smith', site_url: 'https://janesmith.com', order: 1 }
        ]
      }
    ]

    render(<CompactSources sources={sources} />)
    
    // Should show "Authors" (plural)
    const authorsButton = screen.getByText('Authors')
    expect(authorsButton).toBeInTheDocument()
    expect(authorsButton.tagName).toBe('BUTTON') // Should be a button, not a link
    
    // Dropdown should contain both authors
    expect(screen.getByText('John Doe')).toBeInTheDocument()
    expect(screen.getByText('Jane Smith')).toBeInTheDocument()
    expect(screen.getByText('https://johndoe.com')).toBeInTheDocument()
    expect(screen.getByText('https://janesmith.com')).toBeInTheDocument()
  })

  it('shows "Authors" (plural) when 3+ authors have websites', () => {
    const sources = [
      {
        filename: 'test-book.pdf',
        page: 1,
        title: 'Test Book',
        authors: [
          { id: 1, name: 'John Doe', site_url: 'https://johndoe.com', order: 0 },
          { id: 2, name: 'Jane Smith', site_url: 'https://janesmith.com', order: 1 },
          { id: 3, name: 'Bob Johnson', site_url: 'https://bobjohnson.com', order: 2 }
        ]
      }
    ]

    render(<CompactSources sources={sources} />)
    
    // Should show "Authors" (plural)
    const authorsButton = screen.getByText('Authors')
    expect(authorsButton).toBeInTheDocument()
    expect(authorsButton.tagName).toBe('BUTTON')
    
    // All three authors should be in dropdown
    expect(screen.getByText('John Doe')).toBeInTheDocument()
    expect(screen.getByText('Jane Smith')).toBeInTheDocument()
    expect(screen.getByText('Bob Johnson')).toBeInTheDocument()
  })

  it('does not show author button when no authors have websites', () => {
    const sources = [
      {
        filename: 'test-book.pdf',
        page: 1,
        title: 'Test Book',
        authors: [
          { id: 1, name: 'John Doe', site_url: null, order: 0 },
          { id: 2, name: 'Jane Smith', site_url: null, order: 1 }
        ]
      }
    ]

    render(<CompactSources sources={sources} />)
    
    // Should not show any author button
    expect(screen.queryByText('Author')).not.toBeInTheDocument()
    expect(screen.queryByText('Authors')).not.toBeInTheDocument()
  })

  it('handles empty site_url strings correctly', () => {
    const sources = [
      {
        filename: 'test-book.pdf',
        page: 1,
        title: 'Test Book',
        authors: [
          { id: 1, name: 'John Doe', site_url: 'https://johndoe.com', order: 0 },
          { id: 2, name: 'Jane Smith', site_url: '', order: 1 }, // Empty string
          { id: 3, name: 'Bob Johnson', site_url: '   ', order: 2 } // Whitespace only
        ]
      }
    ]

    render(<CompactSources sources={sources} />)
    
    // Should show "Author" (singular) because only one has a valid website
    const authorButton = screen.getByText('Author')
    expect(authorButton).toBeInTheDocument()
    expect(authorButton).toHaveAttribute('href', 'https://johndoe.com')
  })

  it('handles undefined authors array gracefully', () => {
    const sources = [
      {
        filename: 'test-book.pdf',
        page: 1,
        title: 'Test Book',
        author: 'Legacy Author',
        // authors array is undefined
      }
    ]

    render(<CompactSources sources={sources} />)
    
    // Should not crash and should not show author button
    expect(screen.queryByText('Author')).not.toBeInTheDocument()
    expect(screen.queryByText('Authors')).not.toBeInTheDocument()
    
    // Should show legacy author in text
    expect(screen.getByText(/Legacy Author/)).toBeInTheDocument()
  })

  it('handles empty authors array gracefully', () => {
    const sources = [
      {
        filename: 'test-book.pdf',
        page: 1,
        title: 'Test Book',
        author: 'Legacy Author',
        authors: [] // Empty array
      }
    ]

    render(<CompactSources sources={sources} />)
    
    // Should not show author button
    expect(screen.queryByText('Author')).not.toBeInTheDocument()
    expect(screen.queryByText('Authors')).not.toBeInTheDocument()
  })
})
