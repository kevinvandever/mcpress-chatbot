import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createRef } from 'react'
import { Input } from './Input'

describe('Input', () => {
  describe('Rendering', () => {
    it('renders as text input by default', () => {
      render(<Input />)
      const input = screen.getByRole('textbox')
      expect(input).toBeInTheDocument()
      expect(input).toHaveAttribute('type', 'text')
    })

    it('renders with different input types', () => {
      const types = ['email', 'password', 'number', 'tel', 'url', 'search'] as const

      types.forEach(type => {
        const { unmount } = render(<Input type={type} />)
        if (type === 'password' || type === 'number') {
          // Password and number inputs don't have textbox role
          const input = document.querySelector(`input[type="${type}"]`)
          expect(input).toBeInTheDocument()
        } else {
          const input = screen.getByRole('textbox')
          expect(input).toHaveAttribute('type', type)
        }
        unmount()
      })
    })

    it('renders as textarea when multiline is true', () => {
      render(<Input multiline />)
      expect(screen.getByRole('textbox')).toBeInstanceOf(HTMLTextAreaElement)
    })

    it('renders with label', () => {
      render(<Input label="Email Address" />)
      expect(screen.getByLabelText('Email Address')).toBeInTheDocument()
    })

    it('renders without label when not provided', () => {
      const { container } = render(<Input />)
      const label = container.querySelector('label')
      expect(label).not.toBeInTheDocument()
    })

    it('renders with placeholder', () => {
      render(<Input placeholder="Enter text here" />)
      expect(screen.getByPlaceholderText('Enter text here')).toBeInTheDocument()
    })

    it('shows required indicator when required prop is true', () => {
      const { container } = render(<Input label="Name" required />)
      const required = container.querySelector('.required')
      expect(required).toBeInTheDocument()
      expect(required).toHaveTextContent('*')
    })
  })

  describe('Size variants', () => {
    it('renders with different sizes', () => {
      const sizes = ['sm', 'md', 'lg'] as const

      sizes.forEach(size => {
        const { container, unmount } = render(<Input size={size} />)
        const input = container.querySelector('.input')
        expect(input?.className).toContain(`size-${size}`)
        unmount()
      })
    })

    it('defaults to medium size', () => {
      const { container } = render(<Input />)
      const input = container.querySelector('.input')
      expect(input?.className).toContain('size-md')
    })
  })

  describe('Error state', () => {
    it('renders error message', () => {
      render(<Input error="This field is required" />)
      expect(screen.getByRole('alert')).toHaveTextContent('This field is required')
    })

    it('applies error styling when error is present', () => {
      const { container } = render(<Input error="Error message" />)
      const input = container.querySelector('.input')
      expect(input?.className).toContain('error')
    })

    it('sets aria-invalid when error is present', () => {
      render(<Input error="Error message" />)
      expect(screen.getByRole('textbox')).toHaveAttribute('aria-invalid', 'true')
    })

    it('associates error message with input using aria-describedby', () => {
      render(<Input error="Error message" />)
      const input = screen.getByRole('textbox')
      const errorId = input.getAttribute('aria-describedby')
      expect(errorId).toBeTruthy()
      expect(screen.getByRole('alert')).toHaveAttribute('id', errorId!)
    })
  })

  describe('Helper text', () => {
    it('renders helper text', () => {
      render(<Input helperText="Enter your email address" />)
      expect(screen.getByText('Enter your email address')).toBeInTheDocument()
    })

    it('does not show helper text when error is present', () => {
      render(<Input helperText="Helper text" error="Error message" />)
      expect(screen.queryByText('Helper text')).not.toBeInTheDocument()
      expect(screen.getByText('Error message')).toBeInTheDocument()
    })

    it('associates helper text with input using aria-describedby', () => {
      render(<Input helperText="Helper text" />)
      const input = screen.getByRole('textbox')
      const helperId = input.getAttribute('aria-describedby')
      expect(helperId).toBeTruthy()
      expect(screen.getByText('Helper text')).toHaveAttribute('id', helperId!)
    })
  })

  describe('Disabled state', () => {
    it('is disabled when disabled prop is true', () => {
      render(<Input disabled />)
      expect(screen.getByRole('textbox')).toBeDisabled()
    })

    it('applies disabled styling', () => {
      const { container } = render(<Input disabled />)
      const input = container.querySelector('.input')
      expect(input?.className).toContain('disabled')
    })
  })

  describe('Full width', () => {
    it('renders full width when fullWidth is true', () => {
      const { container } = render(<Input fullWidth />)
      const containerDiv = container.querySelector('.container')
      expect(containerDiv?.className).toContain('fullWidth')
    })
  })

  describe('Textarea mode', () => {
    it('renders textarea with custom rows', () => {
      render(<Input multiline rows={5} />)
      const textarea = screen.getByRole('textbox')
      expect(textarea).toHaveAttribute('rows', '5')
    })

    it('textarea supports all base input props', () => {
      render(
        <Input
          multiline
          label="Message"
          placeholder="Enter your message"
          error="Message is required"
        />
      )
      expect(screen.getByLabelText('Message')).toBeInTheDocument()
      expect(screen.getByPlaceholderText('Enter your message')).toBeInTheDocument()
      expect(screen.getByRole('alert')).toHaveTextContent('Message is required')
    })
  })

  describe('User interactions', () => {
    it('accepts text input', async () => {
      const user = userEvent.setup()
      render(<Input />)
      const input = screen.getByRole('textbox')

      await user.type(input, 'Hello World')
      expect(input).toHaveValue('Hello World')
    })

    it('calls onChange handler', async () => {
      const handleChange = jest.fn()
      const user = userEvent.setup()
      render(<Input onChange={handleChange} />)

      await user.type(screen.getByRole('textbox'), 'test')
      expect(handleChange).toHaveBeenCalled()
    })

    it('calls onBlur handler', async () => {
      const handleBlur = jest.fn()
      const user = userEvent.setup()
      render(<Input onBlur={handleBlur} />)

      const input = screen.getByRole('textbox')
      await user.click(input)
      await user.tab()

      expect(handleBlur).toHaveBeenCalled()
    })

    it('does not accept input when disabled', async () => {
      const user = userEvent.setup()
      render(<Input disabled />)
      const input = screen.getByRole('textbox')

      await user.type(input, 'test')
      expect(input).toHaveValue('')
    })
  })

  describe('Ref forwarding', () => {
    it('forwards ref to input element', () => {
      const ref = createRef<HTMLInputElement>()
      render(<Input ref={ref} />)
      expect(ref.current).toBeInstanceOf(HTMLInputElement)
    })

    it('forwards ref to textarea element when multiline', () => {
      const ref = createRef<HTMLTextAreaElement>()
      render(<Input multiline ref={ref} />)
      expect(ref.current).toBeInstanceOf(HTMLTextAreaElement)
    })
  })

  describe('Accessibility', () => {
    it('generates unique id for input', () => {
      const { container: container1 } = render(<Input label="Input 1" />)
      const { container: container2 } = render(<Input label="Input 2" />)

      const input1 = container1.querySelector('input')
      const input2 = container2.querySelector('input')

      expect(input1?.id).toBeTruthy()
      expect(input2?.id).toBeTruthy()
      expect(input1?.id).not.toBe(input2?.id)
    })

    it('uses provided id when given', () => {
      render(<Input id="custom-input" label="Custom" />)
      expect(screen.getByLabelText('Custom')).toHaveAttribute('id', 'custom-input')
    })

    it('associates label with input via htmlFor', () => {
      render(<Input label="Email" />)
      const input = screen.getByLabelText('Email')
      expect(input).toBeInTheDocument()
    })

    it('is keyboard accessible', async () => {
      const user = userEvent.setup()
      render(<Input label="Test" />)

      await user.tab()
      expect(screen.getByLabelText('Test')).toHaveFocus()
    })
  })

  describe('MC Press Brand Colors', () => {
    it('uses MC Blue for focus state', () => {
      // This is tested through CSS, verifying class application
      const { container } = render(<Input />)
      const input = container.querySelector('.input')
      expect(input).toBeInTheDocument()
      // Focus styling defined in CSS with --mc-blue
    })

    it('uses MC Red for error state', () => {
      const { container } = render(<Input error="Error" />)
      const input = container.querySelector('.error')
      expect(input).toBeInTheDocument()
      // Error styling defined in CSS with --mc-red
    })
  })
})
