import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Button } from './Button'

describe('Button', () => {
  describe('Rendering', () => {
    it('renders with text content', () => {
      render(<Button>Click me</Button>)
      expect(screen.getByRole('button', { name: /click me/i })).toBeInTheDocument()
    })

    it('renders with default variant (primary)', () => {
      const { container } = render(<Button>Primary</Button>)
      const button = container.querySelector('button')
      expect(button?.className).toContain('variant-primary')
    })

    it('renders with all variant types', () => {
      const variants = ['primary', 'secondary', 'tertiary', 'danger', 'success', 'cta'] as const

      variants.forEach(variant => {
        const { container } = render(<Button variant={variant}>{variant}</Button>)
        const button = container.querySelector('button')
        expect(button?.className).toContain(`variant-${variant}`)
      })
    })

    it('renders CTA variant for e-commerce actions', () => {
      const { container } = render(<Button variant="cta">Buy Now</Button>)
      const button = container.querySelector('button')
      expect(button?.className).toContain('variant-cta')
    })

    it('renders with different sizes', () => {
      const sizes = ['sm', 'md', 'lg'] as const

      sizes.forEach(size => {
        const { container } = render(<Button size={size}>{size}</Button>)
        const button = container.querySelector('button')
        expect(button?.className).toContain(`size-${size}`)
      })
    })

    it('renders full width when specified', () => {
      const { container } = render(<Button fullWidth>Full Width</Button>)
      const button = container.querySelector('button')
      expect(button?.className).toContain('fullWidth')
    })
  })

  describe('Loading state', () => {
    it('shows spinner when loading', () => {
      render(<Button loading>Loading</Button>)
      expect(screen.getByRole('status', { name: /loading/i })).toBeInTheDocument()
    })

    it('is disabled when loading', () => {
      render(<Button loading>Loading</Button>)
      expect(screen.getByRole('button')).toBeDisabled()
    })

    it('has aria-busy attribute when loading', () => {
      render(<Button loading>Loading</Button>)
      expect(screen.getByRole('button')).toHaveAttribute('aria-busy', 'true')
    })

    it('hides icon when loading', () => {
      const icon = <span data-testid="icon">Icon</span>
      render(
        <Button loading icon={icon}>
          Loading
        </Button>
      )
      expect(screen.queryByTestId('icon')).not.toBeInTheDocument()
    })
  })

  describe('Icon support', () => {
    it('renders icon on the left by default', () => {
      const icon = <span data-testid="icon">→</span>
      const { container } = render(<Button icon={icon}>With Icon</Button>)
      const iconSpan = container.querySelector('.iconLeft')
      expect(iconSpan).toBeInTheDocument()
    })

    it('renders icon on the right when specified', () => {
      const icon = <span data-testid="icon">→</span>
      const { container } = render(
        <Button icon={icon} iconPosition="right">
          With Icon
        </Button>
      )
      const iconSpan = container.querySelector('.iconRight')
      expect(iconSpan).toBeInTheDocument()
    })

    it('hides icon from screen readers', () => {
      const icon = <span data-testid="icon">→</span>
      const { container } = render(<Button icon={icon}>With Icon</Button>)
      const iconSpan = container.querySelector('.iconLeft')
      expect(iconSpan).toHaveAttribute('aria-hidden', 'true')
    })
  })

  describe('Disabled state', () => {
    it('is disabled when disabled prop is true', () => {
      render(<Button disabled>Disabled</Button>)
      expect(screen.getByRole('button')).toBeDisabled()
    })

    it('has aria-disabled attribute', () => {
      render(<Button disabled>Disabled</Button>)
      expect(screen.getByRole('button')).toHaveAttribute('aria-disabled', 'true')
    })
  })

  describe('Interactions', () => {
    it('calls onClick handler when clicked', async () => {
      const handleClick = jest.fn()
      const user = userEvent.setup()

      render(<Button onClick={handleClick}>Click me</Button>)
      await user.click(screen.getByRole('button'))

      expect(handleClick).toHaveBeenCalledTimes(1)
    })

    it('does not call onClick when disabled', async () => {
      const handleClick = jest.fn()
      const user = userEvent.setup()

      render(
        <Button onClick={handleClick} disabled>
          Disabled
        </Button>
      )
      await user.click(screen.getByRole('button'))

      expect(handleClick).not.toHaveBeenCalled()
    })

    it('does not call onClick when loading', async () => {
      const handleClick = jest.fn()
      const user = userEvent.setup()

      render(
        <Button onClick={handleClick} loading>
          Loading
        </Button>
      )
      await user.click(screen.getByRole('button'))

      expect(handleClick).not.toHaveBeenCalled()
    })
  })

  describe('Button type attribute', () => {
    it('defaults to type="button"', () => {
      render(<Button>Button</Button>)
      expect(screen.getByRole('button')).toHaveAttribute('type', 'button')
    })

    it('accepts type="submit"', () => {
      render(<Button type="submit">Submit</Button>)
      expect(screen.getByRole('button')).toHaveAttribute('type', 'submit')
    })

    it('accepts type="reset"', () => {
      render(<Button type="reset">Reset</Button>)
      expect(screen.getByRole('button')).toHaveAttribute('type', 'reset')
    })
  })

  describe('Custom className', () => {
    it('merges custom className with component classes', () => {
      const { container } = render(<Button className="custom-class">Custom</Button>)
      const button = container.querySelector('button')
      expect(button?.className).toContain('custom-class')
      expect(button?.className).toContain('button')
    })
  })

  describe('Accessibility', () => {
    it('has accessible name from children', () => {
      render(<Button>Accessible Button</Button>)
      expect(screen.getByRole('button', { name: /accessible button/i })).toBeInTheDocument()
    })

    it('supports aria-label', () => {
      render(<Button aria-label="Custom label">Icon only</Button>)
      expect(screen.getByRole('button', { name: /custom label/i })).toBeInTheDocument()
    })

    it('is keyboard accessible', async () => {
      const handleClick = jest.fn()
      const user = userEvent.setup()

      render(<Button onClick={handleClick}>Keyboard</Button>)

      // Tab to focus
      await user.tab()
      expect(screen.getByRole('button')).toHaveFocus()

      // Press Enter
      await user.keyboard('{Enter}')
      expect(handleClick).toHaveBeenCalled()
    })

    it('is keyboard accessible with Space', async () => {
      const handleClick = jest.fn()
      const user = userEvent.setup()

      render(<Button onClick={handleClick}>Keyboard</Button>)

      await user.tab()
      await user.keyboard(' ')
      expect(handleClick).toHaveBeenCalled()
    })
  })

  describe('MC Press Brand Colors', () => {
    it('renders primary variant with MC Blue styling', () => {
      const { container } = render(<Button variant="primary">Primary</Button>)
      const button = container.querySelector('.variant-primary')
      expect(button).toBeInTheDocument()
    })

    it('renders CTA variant with MC Orange for e-commerce', () => {
      const { container } = render(<Button variant="cta">Buy Now</Button>)
      const button = container.querySelector('.variant-cta')
      expect(button).toBeInTheDocument()
    })

    it('renders success variant with MC Green', () => {
      const { container } = render(<Button variant="success">Success</Button>)
      const button = container.querySelector('.variant-success')
      expect(button).toBeInTheDocument()
    })

    it('renders danger variant with MC Red', () => {
      const { container } = render(<Button variant="danger">Delete</Button>)
      const button = container.querySelector('.variant-danger')
      expect(button).toBeInTheDocument()
    })
  })
})
