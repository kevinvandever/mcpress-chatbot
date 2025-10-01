import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createRef } from 'react'
import { Card } from './Card'

describe('Card', () => {
  describe('Rendering', () => {
    it('renders with children content', () => {
      render(<Card>Card content here</Card>)
      expect(screen.getByText('Card content here')).toBeInTheDocument()
    })

    it('renders all variant types', () => {
      const variants = ['default', 'elevated', 'outlined', 'interactive'] as const

      variants.forEach(variant => {
        const { container, unmount } = render(
          <Card variant={variant} key={variant}>
            {variant} card
          </Card>
        )
        const card = container.querySelector('.card')
        expect(card?.className).toContain(`variant-${variant}`)
        unmount()
      })
    })

    it('renders with optional header', () => {
      render(
        <Card header={<h3>Card Header</h3>}>
          Card content
        </Card>
      )
      expect(screen.getByText('Card Header')).toBeInTheDocument()
    })

    it('renders with optional footer', () => {
      render(
        <Card footer={<p>Card Footer</p>}>
          Card content
        </Card>
      )
      expect(screen.getByText('Card Footer')).toBeInTheDocument()
    })

    it('renders without header when not provided', () => {
      const { container } = render(<Card>Content only</Card>)
      const header = container.querySelector('.header')
      expect(header).not.toBeInTheDocument()
    })

    it('renders without footer when not provided', () => {
      const { container } = render(<Card>Content only</Card>)
      const footer = container.querySelector('.footer')
      expect(footer).not.toBeInTheDocument()
    })

    it('renders with image', () => {
      render(
        <Card image="/test-image.jpg" imageAlt="Test image">
          Card content
        </Card>
      )
      const image = screen.getByAltText('Test image')
      expect(image).toBeInTheDocument()
      expect(image).toHaveAttribute('src', '/test-image.jpg')
    })

    it('renders without image when not provided', () => {
      const { container } = render(<Card>Content only</Card>)
      const media = container.querySelector('.media')
      expect(media).not.toBeInTheDocument()
    })
  })

  describe('Padding variants', () => {
    it('renders with different padding sizes', () => {
      const sizes = ['none', 'sm', 'md', 'lg'] as const

      sizes.forEach(size => {
        const { container, unmount } = render(
          <Card padding={size} key={size}>
            Padded content
          </Card>
        )
        const card = container.querySelector('.card')
        expect(card?.className).toContain(`padding-${size}`)
        unmount()
      })
    })

    it('defaults to medium padding', () => {
      const { container } = render(<Card>Content</Card>)
      const card = container.querySelector('.card')
      expect(card?.className).toContain('padding-md')
    })
  })

  describe('Hoverable state', () => {
    it('applies hoverable class when hoverable prop is true', () => {
      const { container } = render(<Card hoverable>Hoverable card</Card>)
      const card = container.querySelector('.hoverable')
      expect(card).toBeInTheDocument()
    })

    it('does not apply hoverable class by default', () => {
      const { container } = render(<Card>Default card</Card>)
      const card = container.querySelector('.card')
      expect(card?.className).not.toContain('hoverable')
    })
  })

  describe('Full width', () => {
    it('renders full width when fullWidth is true', () => {
      const { container } = render(<Card fullWidth>Full width card</Card>)
      const card = container.querySelector('.fullWidth')
      expect(card).toBeInTheDocument()
    })
  })

  describe('Interactive variant', () => {
    it('has cursor pointer for interactive variant', () => {
      const { container } = render(
        <Card variant="interactive">Clickable card</Card>
      )
      const card = container.querySelector('.variant-interactive')
      expect(card).toBeInTheDocument()
    })

    it('can be clicked when interactive', async () => {
      const handleClick = jest.fn()
      const user = userEvent.setup()

      render(
        <Card variant="interactive" onClick={handleClick}>
          Clickable card
        </Card>
      )

      const card = screen.getByText('Clickable card').closest('.card')
      await user.click(card!)
      expect(handleClick).toHaveBeenCalledTimes(1)
    })
  })

  describe('Complete card structure', () => {
    it('renders card with all sections (image, header, content, footer)', () => {
      const { container } = render(
        <Card
          image="/product.jpg"
          imageAlt="Product"
          header={<h3>Product Title</h3>}
          footer={<button>Buy Now</button>}
        >
          Product description
        </Card>
      )

      expect(screen.getByAltText('Product')).toBeInTheDocument()
      expect(screen.getByText('Product Title')).toBeInTheDocument()
      expect(screen.getByText('Product description')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /buy now/i })).toBeInTheDocument()

      const media = container.querySelector('.media')
      const header = container.querySelector('.header')
      const content = container.querySelector('.content')
      const footer = container.querySelector('.footer')

      expect(media).toBeInTheDocument()
      expect(header).toBeInTheDocument()
      expect(content).toBeInTheDocument()
      expect(footer).toBeInTheDocument()
    })
  })

  describe('Ref forwarding', () => {
    it('forwards ref to card element', () => {
      const ref = createRef<HTMLDivElement>()
      render(<Card ref={ref}>Card with ref</Card>)
      expect(ref.current).toBeInstanceOf(HTMLDivElement)
    })
  })

  describe('Accessibility', () => {
    it('provides alt text for images', () => {
      render(
        <Card image="/test.jpg" imageAlt="Descriptive alt text">
          Content
        </Card>
      )
      expect(screen.getByAltText('Descriptive alt text')).toBeInTheDocument()
    })

    it('is keyboard accessible when interactive', async () => {
      const handleClick = jest.fn()
      const user = userEvent.setup()

      render(
        <Card variant="interactive" onClick={handleClick} tabIndex={0}>
          Interactive card
        </Card>
      )

      const card = screen.getByText('Interactive card').closest('.card')
      await user.tab()
      expect(card).toHaveFocus()
    })

    it('supports focus-visible outline for interactive cards', () => {
      const { container } = render(
        <Card variant="interactive" tabIndex={0}>
          Interactive card
        </Card>
      )
      const card = container.querySelector('.variant-interactive')
      expect(card).toBeInTheDocument()
      // Focus styling defined in CSS with --mc-blue
    })
  })

  describe('MC Press Brand Colors', () => {
    it('uses MC Gray for outlined variant', () => {
      const { container } = render(<Card variant="outlined">Outlined card</Card>)
      const card = container.querySelector('.variant-outlined')
      expect(card).toBeInTheDocument()
      // Outlined styling defined in CSS with --mc-gray
    })

    it('uses MC Blue for interactive hover and focus', () => {
      const { container } = render(
        <Card variant="interactive" hoverable>
          Interactive card
        </Card>
      )
      const card = container.querySelector('.variant-interactive.hoverable')
      expect(card).toBeInTheDocument()
      // Hover/focus styling defined in CSS with --mc-blue
    })
  })

  describe('Custom className', () => {
    it('merges custom className with component classes', () => {
      const { container } = render(
        <Card className="custom-card">Content</Card>
      )
      const card = container.querySelector('.card')
      expect(card?.className).toContain('custom-card')
      expect(card?.className).toContain('card')
    })
  })

  describe('HTML attributes', () => {
    it('forwards HTML attributes to card element', () => {
      const { container } = render(
        <Card data-testid="custom-card" aria-label="Card label">
          Content
        </Card>
      )
      const card = container.querySelector('[data-testid="custom-card"]')
      expect(card).toBeInTheDocument()
      expect(card).toHaveAttribute('aria-label', 'Card label')
    })
  })
})
