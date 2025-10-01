import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Alert } from './Alert'

describe('Alert', () => {
  describe('Rendering', () => {
    it('renders with message content', () => {
      render(<Alert variant="info">This is an alert message</Alert>)
      expect(screen.getByRole('alert')).toHaveTextContent('This is an alert message')
    })

    it('renders all variant types', () => {
      const variants = ['success', 'error', 'warning', 'info'] as const

      variants.forEach(variant => {
        const { container } = render(
          <Alert variant={variant} key={variant}>
            {variant} message
          </Alert>
        )
        const alert = container.querySelector('.alert')
        expect(alert?.className).toContain(`variant-${variant}`)
      })
    })

    it('renders with optional title', () => {
      render(
        <Alert variant="success" title="Success Title">
          Message content
        </Alert>
      )
      expect(screen.getByText('Success Title')).toBeInTheDocument()
    })

    it('renders without title when not provided', () => {
      const { container } = render(<Alert variant="info">Message only</Alert>)
      const title = container.querySelector('.title')
      expect(title).not.toBeInTheDocument()
    })

    it('renders default icon for each variant', () => {
      const { container } = render(<Alert variant="success">Success</Alert>)
      const icon = container.querySelector('.icon')
      expect(icon).toBeInTheDocument()
    })

    it('renders custom icon when provided', () => {
      const customIcon = <span data-testid="custom-icon">★</span>
      render(
        <Alert variant="info" icon={customIcon}>
          With custom icon
        </Alert>
      )
      expect(screen.getByTestId('custom-icon')).toBeInTheDocument()
    })
  })

  describe('Close button', () => {
    it('does not render close button by default', () => {
      const { container } = render(<Alert variant="info">Message</Alert>)
      const closeButton = container.querySelector('.closeButton')
      expect(closeButton).not.toBeInTheDocument()
    })

    it('renders close button when closable is true', () => {
      render(
        <Alert variant="info" closable>
          Message
        </Alert>
      )
      expect(screen.getByRole('button', { name: /close alert/i })).toBeInTheDocument()
    })

    it('renders close button when onClose is provided', () => {
      const handleClose = jest.fn()
      render(
        <Alert variant="info" onClose={handleClose}>
          Message
        </Alert>
      )
      expect(screen.getByRole('button', { name: /close alert/i })).toBeInTheDocument()
    })

    it('calls onClose when close button is clicked', async () => {
      const handleClose = jest.fn()
      const user = userEvent.setup()

      render(
        <Alert variant="info" closable onClose={handleClose}>
          Message
        </Alert>
      )

      await user.click(screen.getByRole('button', { name: /close alert/i }))
      expect(handleClose).toHaveBeenCalledTimes(1)
    })
  })

  describe('Accessibility', () => {
    it('has role="alert" for screen readers', () => {
      render(<Alert variant="info">Accessible alert</Alert>)
      expect(screen.getByRole('alert')).toBeInTheDocument()
    })

    it('has aria-label on close button', () => {
      render(
        <Alert variant="info" closable>
          Message
        </Alert>
      )
      expect(screen.getByRole('button', { name: /close alert/i })).toHaveAttribute(
        'aria-label',
        'Close alert'
      )
    })

    it('hides icon from screen readers with aria-hidden', () => {
      const { container } = render(<Alert variant="info">Message</Alert>)
      const icon = container.querySelector('.icon')
      expect(icon).toHaveAttribute('aria-hidden', 'true')
    })

    it('close button is keyboard accessible', async () => {
      const handleClose = jest.fn()
      const user = userEvent.setup()

      render(
        <Alert variant="info" closable onClose={handleClose}>
          Message
        </Alert>
      )

      // Tab to close button
      await user.tab()
      expect(screen.getByRole('button', { name: /close alert/i })).toHaveFocus()

      // Press Enter
      await user.keyboard('{Enter}')
      expect(handleClose).toHaveBeenCalled()
    })
  })

  describe('MC Press Brand Colors', () => {
    it('renders success variant with MC Green styling', () => {
      const { container } = render(<Alert variant="success">Success message</Alert>)
      const alert = container.querySelector('.variant-success')
      expect(alert).toBeInTheDocument()
    })

    it('renders error variant with MC Red styling', () => {
      const { container } = render(<Alert variant="error">Error message</Alert>)
      const alert = container.querySelector('.variant-error')
      expect(alert).toBeInTheDocument()
    })

    it('renders warning variant with MC Orange styling', () => {
      const { container } = render(<Alert variant="warning">Warning message</Alert>)
      const alert = container.querySelector('.variant-warning')
      expect(alert).toBeInTheDocument()
    })

    it('renders info variant with MC Blue styling', () => {
      const { container } = render(<Alert variant="info">Info message</Alert>)
      const alert = container.querySelector('.variant-info')
      expect(alert).toBeInTheDocument()
    })
  })

  describe('Custom className', () => {
    it('merges custom className with component classes', () => {
      const { container } = render(
        <Alert variant="info" className="custom-alert">
          Message
        </Alert>
      )
      const alert = container.querySelector('.alert')
      expect(alert?.className).toContain('custom-alert')
      expect(alert?.className).toContain('alert')
    })
  })

  describe('Content rendering', () => {
    it('renders complex content including links', () => {
      render(
        <Alert variant="info">
          This is a message with a <a href="/test">link</a>
        </Alert>
      )
      expect(screen.getByRole('link', { name: /link/i })).toBeInTheDocument()
    })

    it('renders title and message separately', () => {
      const { container } = render(
        <Alert variant="success" title="Success!">
          Operation completed successfully.
        </Alert>
      )
      const title = container.querySelector('.title')
      const message = container.querySelector('.message')
      expect(title).toHaveTextContent('Success!')
      expect(message).toHaveTextContent('Operation completed successfully.')
    })
  })
})
