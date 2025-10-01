import { render, screen } from '@testing-library/react'
import { Badge } from './Badge'

describe('Badge', () => {
  describe('Rendering', () => {
    it('renders with children content', () => {
      render(<Badge>Badge text</Badge>)
      expect(screen.getByText('Badge text')).toBeInTheDocument()
    })

    it('renders all variant types', () => {
      const variants = ['primary', 'success', 'warning', 'danger', 'neutral', 'info'] as const

      variants.forEach(variant => {
        const { container, unmount } = render(
          <Badge variant={variant} key={variant}>
            {variant}
          </Badge>
        )
        const badge = container.querySelector('.badge')
        expect(badge?.className).toContain(`variant-${variant}`)
        unmount()
      })
    })

    it('defaults to neutral variant', () => {
      const { container } = render(<Badge>Default</Badge>)
      const badge = container.querySelector('.badge')
      expect(badge?.className).toContain('variant-neutral')
    })
  })

  describe('Size variants', () => {
    it('renders with different sizes', () => {
      const sizes = ['sm', 'md', 'lg'] as const

      sizes.forEach(size => {
        const { container, unmount } = render(
          <Badge size={size} key={size}>
            Size {size}
          </Badge>
        )
        const badge = container.querySelector('.badge')
        expect(badge?.className).toContain(`size-${size}`)
        unmount()
      })
    })

    it('defaults to medium size', () => {
      const { container } = render(<Badge>Default</Badge>)
      const badge = container.querySelector('.badge')
      expect(badge?.className).toContain('size-md')
    })
  })

  describe('Shape variants', () => {
    it('renders with different shapes', () => {
      const shapes = ['rounded', 'pill'] as const

      shapes.forEach(shape => {
        const { container, unmount } = render(
          <Badge shape={shape} key={shape}>
            Shape {shape}
          </Badge>
        )
        const badge = container.querySelector('.badge')
        expect(badge?.className).toContain(`shape-${shape}`)
        unmount()
      })
    })

    it('defaults to rounded shape', () => {
      const { container } = render(<Badge>Default</Badge>)
      const badge = container.querySelector('.badge')
      expect(badge?.className).toContain('shape-rounded')
    })
  })

  describe('Outlined style', () => {
    it('applies outlined class when outlined is true', () => {
      const { container } = render(<Badge outlined>Outlined badge</Badge>)
      const badge = container.querySelector('.outlined')
      expect(badge).toBeInTheDocument()
    })

    it('does not apply outlined class by default', () => {
      const { container } = render(<Badge>Default badge</Badge>)
      const badge = container.querySelector('.badge')
      expect(badge?.className).not.toContain('outlined')
    })
  })

  describe('Custom className', () => {
    it('merges custom className with component classes', () => {
      const { container } = render(
        <Badge className="custom-badge">Content</Badge>
      )
      const badge = container.querySelector('.badge')
      expect(badge?.className).toContain('custom-badge')
      expect(badge?.className).toContain('badge')
    })
  })

  describe('MC Press Brand Colors', () => {
    it('uses MC Blue for primary variant', () => {
      const { container } = render(<Badge variant="primary">Primary</Badge>)
      const badge = container.querySelector('.variant-primary')
      expect(badge).toBeInTheDocument()
      // Styling defined in CSS with --mc-blue
    })

    it('uses MC Green for success variant', () => {
      const { container } = render(<Badge variant="success">Success</Badge>)
      const badge = container.querySelector('.variant-success')
      expect(badge).toBeInTheDocument()
      // Styling defined in CSS with --mc-green
    })

    it('uses MC Orange for warning variant', () => {
      const { container } = render(<Badge variant="warning">Warning</Badge>)
      const badge = container.querySelector('.variant-warning')
      expect(badge).toBeInTheDocument()
      // Styling defined in CSS with --mc-orange
    })

    it('uses MC Red for danger variant', () => {
      const { container } = render(<Badge variant="danger">Danger</Badge>)
      const badge = container.querySelector('.variant-danger')
      expect(badge).toBeInTheDocument()
      // Styling defined in CSS with --mc-red
    })

    it('uses MC Blue Light for info variant', () => {
      const { container } = render(<Badge variant="info">Info</Badge>)
      const badge = container.querySelector('.variant-info')
      expect(badge).toBeInTheDocument()
      // Styling defined in CSS with --mc-blue-light
    })

    it('uses MC Gray for neutral variant', () => {
      const { container } = render(<Badge variant="neutral">Neutral</Badge>)
      const badge = container.querySelector('.variant-neutral')
      expect(badge).toBeInTheDocument()
      // Styling defined in CSS with --mc-gray
    })
  })

  describe('Content rendering', () => {
    it('renders text content', () => {
      render(<Badge>Text Badge</Badge>)
      expect(screen.getByText('Text Badge')).toBeInTheDocument()
    })

    it('renders numeric content', () => {
      render(<Badge>99+</Badge>)
      expect(screen.getByText('99+')).toBeInTheDocument()
    })

    it('renders complex content', () => {
      render(
        <Badge>
          <span data-testid="icon">★</span> Featured
        </Badge>
      )
      expect(screen.getByTestId('icon')).toBeInTheDocument()
      expect(screen.getByText('Featured')).toBeInTheDocument()
    })
  })

  describe('Combination of props', () => {
    it('renders with multiple style props', () => {
      const { container } = render(
        <Badge variant="success" size="lg" shape="pill" outlined>
          Complete
        </Badge>
      )
      const badge = container.querySelector('.badge')
      expect(badge?.className).toContain('variant-success')
      expect(badge?.className).toContain('size-lg')
      expect(badge?.className).toContain('shape-pill')
      expect(badge?.className).toContain('outlined')
    })
  })
})
