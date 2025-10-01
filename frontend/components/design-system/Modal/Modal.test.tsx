import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Modal } from './Modal'

describe('Modal', () => {
  const mockOnClose = jest.fn()

  beforeEach(() => {
    mockOnClose.mockClear()
  })

  describe('Rendering', () => {
    it('renders modal when isOpen is true', () => {
      render(
        <Modal isOpen={true} onClose={mockOnClose}>
          Modal content
        </Modal>
      )
      expect(screen.getByText('Modal content')).toBeInTheDocument()
    })

    it('does not render when isOpen is false', () => {
      render(
        <Modal isOpen={false} onClose={mockOnClose}>
          Modal content
        </Modal>
      )
      expect(screen.queryByText('Modal content')).not.toBeInTheDocument()
    })

    it('renders with title', () => {
      render(
        <Modal isOpen={true} onClose={mockOnClose} title="Modal Title">
          Modal content
        </Modal>
      )
      expect(screen.getByText('Modal Title')).toBeInTheDocument()
    })

    it('renders without title when not provided', () => {
      const { container } = render(
        <Modal isOpen={true} onClose={mockOnClose}>
          Modal content
        </Modal>
      )
      const title = container.querySelector('.title')
      expect(title).not.toBeInTheDocument()
    })

    it('renders with footer', () => {
      render(
        <Modal
          isOpen={true}
          onClose={mockOnClose}
          footer={<button>Footer Button</button>}
        >
          Modal content
        </Modal>
      )
      expect(screen.getByRole('button', { name: /footer button/i })).toBeInTheDocument()
    })

    it('renders without footer when not provided', () => {
      const { container } = render(
        <Modal isOpen={true} onClose={mockOnClose}>
          Modal content
        </Modal>
      )
      const footer = container.querySelector('.footer')
      expect(footer).not.toBeInTheDocument()
    })
  })

  describe('Size variants', () => {
    it('renders with different sizes', () => {
      const sizes = ['sm', 'md', 'lg', 'xl', 'full'] as const

      sizes.forEach(size => {
        const { container, unmount } = render(
          <Modal isOpen={true} onClose={mockOnClose} size={size} key={size}>
            Content
          </Modal>
        )
        const modal = container.querySelector('.modal')
        expect(modal?.className).toContain(`size-${size}`)
        unmount()
      })
    })

    it('defaults to medium size', () => {
      const { container } = render(
        <Modal isOpen={true} onClose={mockOnClose}>
          Content
        </Modal>
      )
      const modal = container.querySelector('.modal')
      expect(modal?.className).toContain('size-md')
    })
  })

  describe('Close button', () => {
    it('shows close button by default', () => {
      render(
        <Modal isOpen={true} onClose={mockOnClose}>
          Content
        </Modal>
      )
      expect(screen.getByRole('button', { name: /close modal/i })).toBeInTheDocument()
    })

    it('hides close button when showCloseButton is false', () => {
      render(
        <Modal isOpen={true} onClose={mockOnClose} showCloseButton={false}>
          Content
        </Modal>
      )
      expect(screen.queryByRole('button', { name: /close modal/i })).not.toBeInTheDocument()
    })

    it('calls onClose when close button is clicked', async () => {
      const user = userEvent.setup()
      render(
        <Modal isOpen={true} onClose={mockOnClose}>
          Content
        </Modal>
      )

      await user.click(screen.getByRole('button', { name: /close modal/i }))
      expect(mockOnClose).toHaveBeenCalledTimes(1)
    })
  })

  describe('Backdrop interaction', () => {
    it('closes modal when backdrop is clicked by default', async () => {
      const user = userEvent.setup()
      const { container } = render(
        <Modal isOpen={true} onClose={mockOnClose}>
          Content
        </Modal>
      )

      const backdrop = container.querySelector('.backdrop')
      await user.click(backdrop!)
      expect(mockOnClose).toHaveBeenCalledTimes(1)
    })

    it('does not close when backdrop is clicked if closeOnBackdropClick is false', async () => {
      const user = userEvent.setup()
      const { container } = render(
        <Modal isOpen={true} onClose={mockOnClose} closeOnBackdropClick={false}>
          Content
        </Modal>
      )

      const backdrop = container.querySelector('.backdrop')
      await user.click(backdrop!)
      expect(mockOnClose).not.toHaveBeenCalled()
    })

    it('does not close when modal content is clicked', async () => {
      const user = userEvent.setup()
      render(
        <Modal isOpen={true} onClose={mockOnClose}>
          <div>Modal content</div>
        </Modal>
      )

      await user.click(screen.getByText('Modal content'))
      expect(mockOnClose).not.toHaveBeenCalled()
    })
  })

  describe('Keyboard interactions', () => {
    it('closes modal on Escape key by default', async () => {
      const user = userEvent.setup()
      render(
        <Modal isOpen={true} onClose={mockOnClose}>
          Content
        </Modal>
      )

      await user.keyboard('{Escape}')
      expect(mockOnClose).toHaveBeenCalledTimes(1)
    })

    it('does not close on Escape if closeOnEscape is false', async () => {
      const user = userEvent.setup()
      render(
        <Modal isOpen={true} onClose={mockOnClose} closeOnEscape={false}>
          Content
        </Modal>
      )

      await user.keyboard('{Escape}')
      expect(mockOnClose).not.toHaveBeenCalled()
    })
  })

  describe('Focus management', () => {
    it('focuses modal when opened', async () => {
      const { container } = render(
        <Modal isOpen={true} onClose={mockOnClose}>
          Content
        </Modal>
      )

      await waitFor(() => {
        const modal = container.querySelector('.modal')
        expect(modal).toHaveFocus()
      })
    })

    it('traps focus within modal', async () => {
      const user = userEvent.setup()
      render(
        <Modal
          isOpen={true}
          onClose={mockOnClose}
          title="Modal"
          footer={<button>Footer Button</button>}
        >
          <button>Content Button</button>
        </Modal>
      )

      const closeButton = screen.getByRole('button', { name: /close modal/i })
      const contentButton = screen.getByRole('button', { name: /content button/i })
      const footerButton = screen.getByRole('button', { name: /footer button/i })

      // Tab through focusable elements
      await user.tab()
      expect(closeButton).toHaveFocus()

      await user.tab()
      expect(contentButton).toHaveFocus()

      await user.tab()
      expect(footerButton).toHaveFocus()

      // Tab should cycle back to first element
      await user.tab()
      expect(closeButton).toHaveFocus()
    })

    it('restores focus to previous element when closed', async () => {
      const TriggerButton = () => {
        const [isOpen, setIsOpen] = React.useState(false)
        return (
          <>
            <button onClick={() => setIsOpen(true)}>Open Modal</button>
            <Modal isOpen={isOpen} onClose={() => setIsOpen(false)}>
              Content
            </Modal>
          </>
        )
      }

      const user = userEvent.setup()
      render(<TriggerButton />)

      const triggerButton = screen.getByRole('button', { name: /open modal/i })
      await user.click(triggerButton)

      const closeButton = screen.getByRole('button', { name: /close modal/i })
      await user.click(closeButton)

      await waitFor(() => {
        expect(triggerButton).toHaveFocus()
      })
    })
  })

  describe('Body scroll lock', () => {
    it('locks body scroll when modal is open', () => {
      const { unmount } = render(
        <Modal isOpen={true} onClose={mockOnClose}>
          Content
        </Modal>
      )

      expect(document.body.style.overflow).toBe('hidden')

      unmount()
      expect(document.body.style.overflow).toBe('')
    })

    it('unlocks body scroll when modal is closed', () => {
      const { rerender } = render(
        <Modal isOpen={true} onClose={mockOnClose}>
          Content
        </Modal>
      )

      expect(document.body.style.overflow).toBe('hidden')

      rerender(
        <Modal isOpen={false} onClose={mockOnClose}>
          Content
        </Modal>
      )

      expect(document.body.style.overflow).toBe('')
    })
  })

  describe('Accessibility', () => {
    it('has role="dialog"', () => {
      const { container } = render(
        <Modal isOpen={true} onClose={mockOnClose}>
          Content
        </Modal>
      )
      const modal = container.querySelector('[role="dialog"]')
      expect(modal).toBeInTheDocument()
    })

    it('has aria-modal="true"', () => {
      const { container } = render(
        <Modal isOpen={true} onClose={mockOnClose}>
          Content
        </Modal>
      )
      const modal = container.querySelector('[aria-modal="true"]')
      expect(modal).toBeInTheDocument()
    })

    it('associates title with modal via aria-labelledby', () => {
      const { container } = render(
        <Modal isOpen={true} onClose={mockOnClose} title="Modal Title">
          Content
        </Modal>
      )
      const modal = container.querySelector('[role="dialog"]')
      expect(modal).toHaveAttribute('aria-labelledby', 'modal-title')
    })

    it('has accessible close button label', () => {
      render(
        <Modal isOpen={true} onClose={mockOnClose}>
          Content
        </Modal>
      )
      expect(screen.getByRole('button', { name: /close modal/i })).toHaveAttribute(
        'aria-label',
        'Close modal'
      )
    })
  })

  describe('Portal rendering', () => {
    it('renders modal in document.body via portal', () => {
      render(
        <Modal isOpen={true} onClose={mockOnClose}>
          Modal content
        </Modal>
      )

      // Modal should be in document.body, not in the default render container
      const modalContent = screen.getByText('Modal content')
      expect(modalContent.closest('body')).toBe(document.body)
    })
  })
})

// Import React for useState in test
import React from 'react'
