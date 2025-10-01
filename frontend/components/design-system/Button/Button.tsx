import { ButtonHTMLAttributes, ReactNode } from 'react'
import styles from './Button.module.css'

export type ButtonVariant = 'primary' | 'secondary' | 'tertiary' | 'danger' | 'success' | 'cta'
export type ButtonSize = 'sm' | 'md' | 'lg'

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  /**
   * Visual style variant
   * - primary: MC Blue for standard actions
   * - cta: MC Orange for high-priority conversion actions (e.g., "Buy Now")
   * - success: MC Green for positive confirmations
   * - danger: MC Red for destructive actions
   * - secondary: Outlined style
   * - tertiary: Text-only style
   */
  variant?: ButtonVariant

  /**
   * Size of the button
   */
  size?: ButtonSize

  /**
   * Show loading spinner and disable interaction
   */
  loading?: boolean

  /**
   * Icon element to display alongside text
   */
  icon?: ReactNode

  /**
   * Position of the icon relative to the text
   */
  iconPosition?: 'left' | 'right'

  /**
   * Make button full width of container
   */
  fullWidth?: boolean

  /**
   * Button text content
   */
  children: ReactNode
}

/**
 * Button component implementing MC Press brand colors and design system
 *
 * Critical: CTA variant uses Orange (#EF9537) per David's requirements for e-commerce
 *
 * @example
 * ```tsx
 * <Button variant="primary">Primary Action</Button>
 * <Button variant="cta" icon={<ShoppingCart />}>Buy Now</Button>
 * <Button variant="danger" size="sm">Delete</Button>
 * <Button loading>Processing...</Button>
 * ```
 */
export const Button = ({
  variant = 'primary',
  size = 'md',
  loading = false,
  icon,
  iconPosition = 'left',
  fullWidth = false,
  disabled,
  children,
  className = '',
  type = 'button',
  ...props
}: ButtonProps) => {
  const classNames = [
    styles.button,
    styles[`variant-${variant}`],
    styles[`size-${size}`],
    fullWidth && styles.fullWidth,
    loading && styles.loading,
    className
  ].filter(Boolean).join(' ')

  const isDisabled = disabled || loading

  return (
    <button
      type={type}
      className={classNames}
      disabled={isDisabled}
      aria-busy={loading}
      aria-disabled={isDisabled}
      {...props}
    >
      {loading && <span className={styles.spinner} aria-label="Loading" role="status" />}
      {!loading && icon && iconPosition === 'left' && (
        <span className={styles.iconLeft} aria-hidden="true">{icon}</span>
      )}
      <span className={styles.label}>{children}</span>
      {!loading && icon && iconPosition === 'right' && (
        <span className={styles.iconRight} aria-hidden="true">{icon}</span>
      )}
    </button>
  )
}

Button.displayName = 'Button'
