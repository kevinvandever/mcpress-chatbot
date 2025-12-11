import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import axios from 'axios'
import MultiAuthorInput from './MultiAuthorInput'

// Mock axios
jest.mock('axios')
const mockedAxios = axios as jest.Mocked<typeof axios>

// Mock API URL
jest.mock('../config/api', () => ({
  API_URL: 'http://localhost:8000'
}))

describe('MultiAuthorInput', () => {
  const mockAuthors = [
    { id: 1, name: 'John Doe', site_url: 'https://johndoe.com', order: 0 },
    { id: 2, name: 'Jane Smith', site_url: 'https://janesmith.com', order: 1 }
  ]

  const mockSearchResults = [
    { id: 3, name: 'Bob Wilson', site_url: 'https://bobwilson.com', document_count: 5 },
    { id: 4, name: 'Alice Brown', site_url: 'https://alicebrown.com', document_count: 3 }
  ]

  const defaultProps = {
    authors: [],
    onChange: jest.fn()
  }

  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe('Rendering', () => {
    it('renders search input with placeholder', () => {
      render(<MultiAuthorInput {...defaultProps} />)
      expect(screen.getByPlaceholderText('Search for authors...')).toBeInTheDocument()
    })

    it('renders custom placeholder', () => {
      render(<MultiAuthorInput {...defaultProps} placeholder="Find authors..." />)
      expect(screen.getByPlaceholderText('Find authors...')).toBeInTheDocument()
    })

    it('shows empty state when no authors', () => {
      render(<MultiAuthorInput {...defaultProps} />)
      expect(screen.getByText('No authors added yet')).toBeInTheDocument()
      expect(screen.getByText('Search and add authors above')).toBeInTheDocument()
    })

    it('renders existing authors', () => {
      render(<MultiAuthorInput {...defaultProps} authors={mockAuthors} />)
      expect(screen.getByText('John Doe')).toBeInTheDocument()
      expect(screen.getByText('Jane Smith')).toBeInTheDocument()
      expect(screen.getByText('Authors (2)')).toBeInTheDocument()
    })

    it('shows author order badges', () => {
      render(<MultiAuthorInput {...defaultProps} authors={mockAuthors} />)
      expect(screen.getByText('1')).toBeInTheDocument()
      expect(screen.getByText('2')).toBeInTheDocument()
    })

    it('displays author website URLs as links', () => {
      render(<MultiAuthorInput {...defaultProps} authors={mockAuthors} />)
      const johnLink = screen.getByRole('link', { name: 'https://johndoe.com' })
      const janeLink = screen.getByRole('link', { name: 'https://janesmith.com' })
      
      expect(johnLink).toHaveAttribute('href', 'https://johndoe.com')
      expect(janeLink).toHaveAttribute('href', 'https://janesmith.com')
      expect(johnLink).toHaveAttribute('target', '_blank')
      expect(janeLink).toHaveAttribute('target', '_blank')
    })
  })

  describe('Search functionality', () => {
    it('performs search when typing', async () => {
      mockedAxios.get.mockResolvedValue({ data: mockSearchResults })
      const user = userEvent.setup()

      render(<MultiAuthorInput {...defaultProps} />)
      const searchInput = screen.getByPlaceholderText('Search for authors...')

      await user.type(searchInput, 'Bob')

      await waitFor(() => {
        expect(mockedAxios.get).toHaveBeenCalledWith(
          'http://localhost:8000/api/authors/search',
          { params: { q: 'Bob', limit: 10 } }
        )
      })
    })

    it('shows search results in dropdown', async () => {
      mockedAxios.get.mockResolvedValue({ data: mockSearchResults })
      const user = userEvent.setup()

      render(<MultiAuthorInput {...defaultProps} />)
      const searchInput = screen.getByPlaceholderText('Search for authors...')

      await user.type(searchInput, 'Bob')

      await waitFor(() => {
        expect(screen.getByText('Bob Wilson')).toBeInTheDocument()
        expect(screen.getByText('Alice Brown')).toBeInTheDocument()
        expect(screen.getByText('5 docs')).toBeInTheDocument()
        expect(screen.getByText('3 docs')).toBeInTheDocument()
      })
    })

    it('shows "Add new author" option for new names', async () => {
      mockedAxios.get.mockResolvedValue({ data: [] })
      const user = userEvent.setup()

      render(<MultiAuthorInput {...defaultProps} />)
      const searchInput = screen.getByPlaceholderText('Search for authors...')

      await user.type(searchInput, 'New Author')

      await waitFor(() => {
        expect(screen.getByText('Add new author: "New Author"')).toBeInTheDocument()
      })
    })

    it('filters out existing authors from search results', async () => {
      mockedAxios.get.mockResolvedValue({ data: [
        ...mockSearchResults,
        { id: 1, name: 'John Doe', site_url: 'https://johndoe.com', document_count: 2 }
      ]})
      const user = userEvent.setup()

      render(<MultiAuthorInput {...defaultProps} authors={mockAuthors} />)
      const searchInput = screen.getByPlaceholderText('Search for authors...')

      await user.type(searchInput, 'John')

      await waitFor(() => {
        expect(screen.queryByText('John Doe')).not.toBeInTheDocument() // Should be filtered out
        expect(screen.getByText('Bob Wilson')).toBeInTheDocument()
        expect(screen.getByText('Alice Brown')).toBeInTheDocument()
      })
    })
  })

  describe('Adding authors', () => {
    it('adds author from search results', async () => {
      mockedAxios.get.mockResolvedValue({ data: mockSearchResults })
      const onChange = jest.fn()
      const user = userEvent.setup()

      render(<MultiAuthorInput {...defaultProps} onChange={onChange} />)
      const searchInput = screen.getByPlaceholderText('Search for authors...')

      await user.type(searchInput, 'Bob')
      
      await waitFor(() => {
        expect(screen.getByText('Bob Wilson')).toBeInTheDocument()
      })

      await user.click(screen.getByText('Bob Wilson'))

      expect(onChange).toHaveBeenCalledWith([{
        id: 3,
        name: 'Bob Wilson',
        site_url: 'https://bobwilson.com',
        order: 0
      }])
    })

    it('adds new author when clicking "Add new author"', async () => {
      mockedAxios.get.mockResolvedValue({ data: [] })
      const onChange = jest.fn()
      const user = userEvent.setup()

      render(<MultiAuthorInput {...defaultProps} onChange={onChange} />)
      const searchInput = screen.getByPlaceholderText('Search for authors...')

      await user.type(searchInput, 'New Author')
      
      await waitFor(() => {
        expect(screen.getByText('Add new author: "New Author"')).toBeInTheDocument()
      })

      await user.click(screen.getByText('Add new author: "New Author"'))

      expect(onChange).toHaveBeenCalledWith([{
        name: 'New Author',
        order: 0
      }])
    })

    it('prevents adding more than maxAuthors', async () => {
      const manyAuthors = Array.from({ length: 5 }, (_, i) => ({
        id: i + 1,
        name: `Author ${i + 1}`,
        order: i
      }))

      mockedAxios.get.mockResolvedValue({ data: mockSearchResults })
      const onChange = jest.fn()
      const user = userEvent.setup()

      render(
        <MultiAuthorInput 
          {...defaultProps} 
          authors={manyAuthors}
          onChange={onChange}
          maxAuthors={5}
        />
      )

      const searchInput = screen.getByPlaceholderText('Maximum 5 authors reached')
      expect(searchInput).toBeDisabled()
    })
  })

  describe('Author management', () => {
    it('removes author when clicking remove button', async () => {
      const onChange = jest.fn()
      const user = userEvent.setup()

      render(<MultiAuthorInput {...defaultProps} authors={mockAuthors} onChange={onChange} />)
      
      // Find remove buttons (trash icons)
      const removeButtons = screen.getAllByTitle('Remove author')
      await user.click(removeButtons[1]) // Remove Jane Smith

      expect(onChange).toHaveBeenCalledWith([{
        id: 1,
        name: 'John Doe',
        site_url: 'https://johndoe.com',
        order: 0
      }])
    })

    it('prevents removing last author', async () => {
      const singleAuthor = [mockAuthors[0]]
      const onChange = jest.fn()
      const user = userEvent.setup()

      // Mock window.alert
      const alertSpy = jest.spyOn(window, 'alert').mockImplementation(() => {})

      render(<MultiAuthorInput {...defaultProps} authors={singleAuthor} onChange={onChange} />)
      
      const removeButton = screen.getByTitle('Cannot remove last author')
      expect(removeButton).toBeDisabled()
    })

    it('moves author up when clicking up arrow', async () => {
      const onChange = jest.fn()
      const user = userEvent.setup()

      render(<MultiAuthorInput {...defaultProps} authors={mockAuthors} onChange={onChange} />)
      
      const upButtons = screen.getAllByTitle('Move up')
      await user.click(upButtons[1]) // Move Jane Smith up

      expect(onChange).toHaveBeenCalledWith([
        { id: 2, name: 'Jane Smith', site_url: 'https://janesmith.com', order: 0 },
        { id: 1, name: 'John Doe', site_url: 'https://johndoe.com', order: 1 }
      ])
    })

    it('moves author down when clicking down arrow', async () => {
      const onChange = jest.fn()
      const user = userEvent.setup()

      render(<MultiAuthorInput {...defaultProps} authors={mockAuthors} onChange={onChange} />)
      
      const downButtons = screen.getAllByTitle('Move down')
      await user.click(downButtons[0]) // Move John Doe down

      expect(onChange).toHaveBeenCalledWith([
        { id: 2, name: 'Jane Smith', site_url: 'https://janesmith.com', order: 0 },
        { id: 1, name: 'John Doe', site_url: 'https://johndoe.com', order: 1 }
      ])
    })

    it('disables move up for first author', () => {
      render(<MultiAuthorInput {...defaultProps} authors={mockAuthors} />)
      
      const upButtons = screen.getAllByTitle('Move up')
      expect(upButtons[0]).toBeDisabled() // First author can't move up
      expect(upButtons[1]).not.toBeDisabled() // Second author can move up
    })

    it('disables move down for last author', () => {
      render(<MultiAuthorInput {...defaultProps} authors={mockAuthors} />)
      
      const downButtons = screen.getAllByTitle('Move down')
      expect(downButtons[0]).not.toBeDisabled() // First author can move down
      expect(downButtons[1]).toBeDisabled() // Last author can't move down
    })
  })

  describe('URL editing', () => {
    it('shows edit input when clicking edit URL button', async () => {
      const user = userEvent.setup()

      render(<MultiAuthorInput {...defaultProps} authors={mockAuthors} />)
      
      const editButtons = screen.getAllByTitle('Edit website URL')
      await user.click(editButtons[0])

      expect(screen.getByDisplayValue('https://johndoe.com')).toBeInTheDocument()
    })

    it('saves URL when clicking save button', async () => {
      const onChange = jest.fn()
      const user = userEvent.setup()

      render(<MultiAuthorInput {...defaultProps} authors={mockAuthors} onChange={onChange} />)
      
      const editButtons = screen.getAllByTitle('Edit website URL')
      await user.click(editButtons[0])

      const urlInput = screen.getByDisplayValue('https://johndoe.com')
      await user.clear(urlInput)
      await user.type(urlInput, 'https://newsite.com')

      const saveButton = screen.getByTitle('Save URL')
      await user.click(saveButton)

      expect(onChange).toHaveBeenCalledWith([
        { id: 1, name: 'John Doe', site_url: 'https://newsite.com', order: 0 },
        { id: 2, name: 'Jane Smith', site_url: 'https://janesmith.com', order: 1 }
      ])
    })

    it('validates URL format', async () => {
      const onChange = jest.fn()
      const user = userEvent.setup()

      // Mock window.alert
      const alertSpy = jest.spyOn(window, 'alert').mockImplementation(() => {})

      render(<MultiAuthorInput {...defaultProps} authors={mockAuthors} onChange={onChange} />)
      
      const editButtons = screen.getAllByTitle('Edit website URL')
      await user.click(editButtons[0])

      const urlInput = screen.getByDisplayValue('https://johndoe.com')
      await user.clear(urlInput)
      await user.type(urlInput, 'invalid-url')

      const saveButton = screen.getByTitle('Save URL')
      await user.click(saveButton)

      expect(alertSpy).toHaveBeenCalledWith('Please enter a valid URL (must start with http:// or https://)')
      expect(onChange).not.toHaveBeenCalled()

      alertSpy.mockRestore()
    })
  })

  describe('Keyboard navigation', () => {
    it('navigates search results with arrow keys', async () => {
      mockedAxios.get.mockResolvedValue({ data: mockSearchResults })
      const user = userEvent.setup()

      render(<MultiAuthorInput {...defaultProps} />)
      const searchInput = screen.getByPlaceholderText('Search for authors...')

      await user.type(searchInput, 'Bob')
      
      await waitFor(() => {
        expect(screen.getByText('Bob Wilson')).toBeInTheDocument()
      })

      // Arrow down to select first result
      await user.keyboard('{ArrowDown}')
      
      // Enter to select
      await user.keyboard('{Enter}')

      expect(defaultProps.onChange).toHaveBeenCalledWith([{
        id: 3,
        name: 'Bob Wilson',
        site_url: 'https://bobwilson.com',
        order: 0
      }])
    })

    it('closes dropdown with Escape key', async () => {
      mockedAxios.get.mockResolvedValue({ data: mockSearchResults })
      const user = userEvent.setup()

      render(<MultiAuthorInput {...defaultProps} />)
      const searchInput = screen.getByPlaceholderText('Search for authors...')

      await user.type(searchInput, 'Bob')
      
      await waitFor(() => {
        expect(screen.getByText('Bob Wilson')).toBeInTheDocument()
      })

      await user.keyboard('{Escape}')

      expect(screen.queryByText('Bob Wilson')).not.toBeInTheDocument()
    })
  })

  describe('Disabled state', () => {
    it('disables search input when disabled', () => {
      render(<MultiAuthorInput {...defaultProps} disabled />)
      expect(screen.getByPlaceholderText('Search for authors...')).toBeDisabled()
    })

    it('disables all author controls when disabled', () => {
      render(<MultiAuthorInput {...defaultProps} authors={mockAuthors} disabled />)
      
      expect(screen.queryByTitle('Edit website URL')).not.toBeInTheDocument()
      expect(screen.queryByTitle('Remove author')).not.toBeInTheDocument()
      expect(screen.queryByTitle('Move up')).not.toBeInTheDocument()
      expect(screen.queryByTitle('Move down')).not.toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('has proper ARIA attributes', () => {
      render(<MultiAuthorInput {...defaultProps} />)
      const searchInput = screen.getByPlaceholderText('Search for authors...')
      
      expect(searchInput).toHaveAttribute('type', 'text')
    })

    it('provides helpful text for screen readers', () => {
      render(<MultiAuthorInput {...defaultProps} />)
      
      expect(screen.getByText('• Type to search existing authors or add new ones')).toBeInTheDocument()
      expect(screen.getByText('• Use drag handles or arrow buttons to reorder')).toBeInTheDocument()
      expect(screen.getByText('• Click website links to edit author URLs')).toBeInTheDocument()
      expect(screen.getByText('• Documents must have at least one author')).toBeInTheDocument()
    })
  })
})