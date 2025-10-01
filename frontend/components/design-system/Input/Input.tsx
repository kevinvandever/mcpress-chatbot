import { InputHTMLAttributes, TextareaHTMLAttributes, forwardRef } from 'react'
import styles from './Input.module.css'

type InputType = 'text' | 'email' | 'password' | 'number' | 'tel' | 'url' | 'search'

interface BaseInputProps {
  /**
   * Label text for the input
   */
  label?: string

  /**
   * Error message to display
   */
  error?: string

  /**
   * Helper text to display below input
   */
  helperText?: string

  /**
   * Full width input
   */
  fullWidth?: boolean

  /**
   * Input size variant
   */
  size?: 'sm' | 'md' | 'lg'
}

export interface StandardInputProps
  extends BaseInputProps,
    Omit<InputHTMLAttributes<HTMLInputElement>, 'size'> {
  /**
   * Input type
   */
  type?: InputType

  /**
   * Use textarea instead of input
   */
  multiline?: false
}

export interface TextareaInputProps
  extends BaseInputProps,
    Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, 'size'> {
  /**
   * Use textarea instead of input
   */
  multiline: true

  /**
   * Number of visible text rows
   */
  rows?: number
}

export type InputProps = StandardInputProps | TextareaInputProps

/**
 * Input component with MC Press design system styling
 *
 * Supports various input types and textarea mode with consistent styling
 * Uses MC Blue for focus states and MC Red for error states
 *
 * @example
 * ```tsx
 * <Input
 *   label="Email"
 *   type="email"
 *   placeholder="Enter your email"
 * />
 *
 * <Input
 *   label="Message"
 *   multiline
 *   rows={4}
 *   placeholder="Enter your message"
 * />
 *
 * <Input
 *   label="Password"
 *   type="password"
 *   error="Password is required"
 * />
 * ```
 */
export const Input = forwardRef<HTMLInputElement | HTMLTextAreaElement, InputProps>(
  (
    {
      label,
      error,
      helperText,
      fullWidth = false,
      size = 'md',
      className = '',
      id,
      ...props
    },
    ref
  ) => {
    const inputId = id || `input-${Math.random().toString(36).substr(2, 9)}`
    const hasError = Boolean(error)

    const containerClasses = [
      styles.container,
      fullWidth && styles.fullWidth,
      className
    ].filter(Boolean).join(' ')

    const inputClasses = [
      styles.input,
      styles[`size-${size}`],
      hasError && styles.error,
      props.disabled && styles.disabled
    ].filter(Boolean).join(' ')

    const renderInput = () => {
      if ('multiline' in props && props.multiline) {
        const { multiline, ...textareaProps } = props
        return (
          <textarea
            ref={ref as React.Ref<HTMLTextAreaElement>}
            id={inputId}
            className={inputClasses}
            aria-invalid={hasError}
            aria-describedby={
              error
                ? `${inputId}-error`
                : helperText
                ? `${inputId}-helper`
                : undefined
            }
            {...textareaProps}
          />
        )
      }

      const { type = 'text', ...inputProps } = props as StandardInputProps
      return (
        <input
          ref={ref as React.Ref<HTMLInputElement>}
          type={type}
          id={inputId}
          className={inputClasses}
          aria-invalid={hasError}
          aria-describedby={
            error
              ? `${inputId}-error`
              : helperText
              ? `${inputId}-helper`
              : undefined
          }
          {...inputProps}
        />
      )
    }

    return (
      <div className={containerClasses}>
        {label && (
          <label htmlFor={inputId} className={styles.label}>
            {label}
            {props.required && <span className={styles.required}>*</span>}
          </label>
        )}
        {renderInput()}
        {error && (
          <p id={`${inputId}-error`} className={styles.errorText} role="alert">
            {error}
          </p>
        )}
        {helperText && !error && (
          <p id={`${inputId}-helper`} className={styles.helperText}>
            {helperText}
          </p>
        )}
      </div>
    )
  }
)

Input.displayName = 'Input'
