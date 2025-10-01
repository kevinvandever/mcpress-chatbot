import { render, screen } from '@testing-library/react'
import { Spinner } from './Spinner'
import { Skeleton } from './Skeleton'
import { ProgressBar } from './ProgressBar'

describe('Spinner', () => {
  describe('Rendering', () => {
    it('renders with default props', () => {
      const { container } = render(<Spinner />)
      expect(container.querySelector('.spinner')).toBeInTheDocument()
    })

    it('renders with different sizes', () => {
      const sizes = ['sm', 'md', 'lg', 'xl'] as const

      sizes.forEach(size => {
        const { container, unmount } = render(<Spinner size={size} key={size} />)
        const spinner = container.querySelector('.spinner')
        expect(spinner?.className).toContain(`spinner-${size}`)
        unmount()
      })
    })

    it('renders with different variants', () => {
      const variants = ['primary', 'secondary', 'white'] as const

      variants.forEach(variant => {
        const { container, unmount } = render(<Spinner variant={variant} key={variant} />)
        const spinner = container.querySelector('.spinner')
        expect(spinner?.className).toContain(`spinner-${variant}`)
        unmount()
      })
    })

    it('defaults to medium size and primary variant', () => {
      const { container } = render(<Spinner />)
      const spinner = container.querySelector('.spinner')
      expect(spinner?.className).toContain('spinner-md')
      expect(spinner?.className).toContain('spinner-primary')
    })
  })

  describe('Accessibility', () => {
    it('has role="status"', () => {
      const { container } = render(<Spinner />)
      expect(container.querySelector('[role="status"]')).toBeInTheDocument()
    })

    it('has aria-label', () => {
      const { container } = render(<Spinner label="Loading content" />)
      const spinner = container.querySelector('[role="status"]')
      expect(spinner).toHaveAttribute('aria-label', 'Loading content')
    })

    it('has default aria-label', () => {
      const { container } = render(<Spinner />)
      const spinner = container.querySelector('[role="status"]')
      expect(spinner).toHaveAttribute('aria-label', 'Loading...')
    })

    it('has visually hidden text for screen readers', () => {
      render(<Spinner label="Loading content" />)
      expect(screen.getByText('Loading content')).toBeInTheDocument()
    })
  })

  describe('MC Press Brand Colors', () => {
    it('uses MC Blue for primary variant', () => {
      const { container } = render(<Spinner variant="primary" />)
      const spinner = container.querySelector('.spinner-primary')
      expect(spinner).toBeInTheDocument()
    })
  })
})

describe('Skeleton', () => {
  describe('Rendering', () => {
    it('renders with default props', () => {
      const { container } = render(<Skeleton />)
      expect(container.querySelector('.skeleton')).toBeInTheDocument()
    })

    it('renders with different variants', () => {
      const variants = ['text', 'circular', 'rectangular'] as const

      variants.forEach(variant => {
        const { container, unmount } = render(<Skeleton variant={variant} key={variant} />)
        const skeleton = container.querySelector('.skeleton')
        expect(skeleton?.className).toContain(`skeleton-${variant}`)
        unmount()
      })
    })

    it('applies custom width', () => {
      const { container } = render(<Skeleton width="200px" />)
      const skeleton = container.querySelector('.skeleton')
      expect(skeleton).toHaveStyle({ width: '200px' })
    })

    it('applies custom height', () => {
      const { container } = render(<Skeleton height="100px" />)
      const skeleton = container.querySelector('.skeleton')
      expect(skeleton).toHaveStyle({ height: '100px' })
    })

    it('accepts numeric width and height', () => {
      const { container } = render(<Skeleton width={200} height={100} />)
      const skeleton = container.querySelector('.skeleton')
      expect(skeleton).toHaveStyle({ width: '200px', height: '100px' })
    })

    it('shows animation by default', () => {
      const { container } = render(<Skeleton />)
      const skeleton = container.querySelector('.skeleton')
      expect(skeleton?.className).toContain('skeletonAnimation')
    })

    it('can disable animation', () => {
      const { container } = render(<Skeleton animation={false} />)
      const skeleton = container.querySelector('.skeleton')
      expect(skeleton?.className).not.toContain('skeletonAnimation')
    })

    it('applies custom className', () => {
      const { container } = render(<Skeleton className="custom-skeleton" />)
      const skeleton = container.querySelector('.skeleton')
      expect(skeleton?.className).toContain('custom-skeleton')
    })
  })

  describe('Accessibility', () => {
    it('has aria-busy="true"', () => {
      const { container } = render(<Skeleton />)
      const skeleton = container.querySelector('.skeleton')
      expect(skeleton).toHaveAttribute('aria-busy', 'true')
    })

    it('has aria-live="polite"', () => {
      const { container } = render(<Skeleton />)
      const skeleton = container.querySelector('.skeleton')
      expect(skeleton).toHaveAttribute('aria-live', 'polite')
    })
  })

  describe('MC Press Brand Colors', () => {
    it('uses MC Gray for skeleton background', () => {
      const { container } = render(<Skeleton />)
      const skeleton = container.querySelector('.skeleton')
      expect(skeleton).toBeInTheDocument()
      // Background styling defined in CSS with --mc-gray
    })
  })
})

describe('ProgressBar', () => {
  describe('Rendering', () => {
    it('renders with default props', () => {
      const { container } = render(<ProgressBar />)
      expect(container.querySelector('.progressBar')).toBeInTheDocument()
    })

    it('renders with different sizes', () => {
      const sizes = ['sm', 'md', 'lg'] as const

      sizes.forEach(size => {
        const { container, unmount } = render(<ProgressBar size={size} key={size} />)
        const progressBar = container.querySelector('.progressBar')
        expect(progressBar?.className).toContain(`progress-${size}`)
        unmount()
      })
    })

    it('renders with different variants', () => {
      const variants = ['primary', 'success', 'warning', 'danger'] as const

      variants.forEach(variant => {
        const { container, unmount } = render(<ProgressBar variant={variant} key={variant} />)
        const progressFill = container.querySelector('.progressFill')
        expect(progressFill?.className).toContain(`progress-${variant}`)
        unmount()
      })
    })

    it('displays progress value', () => {
      const { container } = render(<ProgressBar value={75} />)
      const progressFill = container.querySelector('.progressFill') as HTMLElement
      expect(progressFill).toHaveStyle({ width: '75%' })
    })

    it('normalizes progress value to 0-100 range', () => {
      const { container: container1 } = render(<ProgressBar value={-10} />)
      const progressFill1 = container1.querySelector('.progressFill') as HTMLElement
      expect(progressFill1).toHaveStyle({ width: '0%' })

      const { container: container2 } = render(<ProgressBar value={150} />)
      const progressFill2 = container2.querySelector('.progressFill') as HTMLElement
      expect(progressFill2).toHaveStyle({ width: '100%' })
    })

    it('shows label when showLabel is true', () => {
      render(<ProgressBar value={75} showLabel />)
      expect(screen.getByText('75%')).toBeInTheDocument()
    })

    it('hides label by default', () => {
      render(<ProgressBar value={75} />)
      expect(screen.queryByText('75%')).not.toBeInTheDocument()
    })

    it('renders indeterminate progress', () => {
      const { container } = render(<ProgressBar indeterminate />)
      const progressFill = container.querySelector('.progressIndeterminate')
      expect(progressFill).toBeInTheDocument()
    })

    it('does not show label in indeterminate mode', () => {
      render(<ProgressBar indeterminate showLabel />)
      expect(screen.queryByText(/\d+%/)).not.toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('has role="progressbar"', () => {
      const { container } = render(<ProgressBar value={50} />)
      expect(container.querySelector('[role="progressbar"]')).toBeInTheDocument()
    })

    it('has aria-valuenow attribute', () => {
      const { container } = render(<ProgressBar value={50} />)
      const progressBar = container.querySelector('[role="progressbar"]')
      expect(progressBar).toHaveAttribute('aria-valuenow', '50')
    })

    it('has aria-valuemin and aria-valuemax', () => {
      const { container } = render(<ProgressBar value={50} />)
      const progressBar = container.querySelector('[role="progressbar"]')
      expect(progressBar).toHaveAttribute('aria-valuemin', '0')
      expect(progressBar).toHaveAttribute('aria-valuemax', '100')
    })

    it('has aria-label', () => {
      const { container } = render(<ProgressBar value={50} label="Loading content" />)
      const progressBar = container.querySelector('[role="progressbar"]')
      expect(progressBar).toHaveAttribute('aria-label', 'Loading content')
    })

    it('has default aria-label with percentage', () => {
      const { container } = render(<ProgressBar value={75} />)
      const progressBar = container.querySelector('[role="progressbar"]')
      expect(progressBar).toHaveAttribute('aria-label', '75% complete')
    })

    it('does not have aria-valuenow in indeterminate mode', () => {
      const { container } = render(<ProgressBar indeterminate />)
      const progressBar = container.querySelector('[role="progressbar"]')
      expect(progressBar).not.toHaveAttribute('aria-valuenow')
    })
  })

  describe('MC Press Brand Colors', () => {
    it('uses MC Blue for primary variant', () => {
      const { container } = render(<ProgressBar variant="primary" />)
      const progressFill = container.querySelector('.progress-primary')
      expect(progressFill).toBeInTheDocument()
    })

    it('uses MC Green for success variant', () => {
      const { container } = render(<ProgressBar variant="success" />)
      const progressFill = container.querySelector('.progress-success')
      expect(progressFill).toBeInTheDocument()
    })

    it('uses MC Orange for warning variant', () => {
      const { container } = render(<ProgressBar variant="warning" />)
      const progressFill = container.querySelector('.progress-warning')
      expect(progressFill).toBeInTheDocument()
    })

    it('uses MC Red for danger variant', () => {
      const { container } = render(<ProgressBar variant="danger" />)
      const progressFill = container.querySelector('.progress-danger')
      expect(progressFill).toBeInTheDocument()
    })
  })
})
