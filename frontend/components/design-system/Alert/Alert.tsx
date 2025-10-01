import { ReactNode } from 'react'
import styles from './Alert.module.css'

export type AlertVariant = 'success' | 'error' | 'warning' | 'info'

export interface AlertProps {
  /**
   * Alert type determining color scheme
   * - success: Green for positive confirmations
   * - error: Red for errors and failures
   * - warning: Orange for warnings and cautions
   * - info: Blue for informational messages
   */
  variant: AlertVariant

  /**
   * Optional title/heading for the alert
   */
  title?: string

  /**
   * Alert message content
   */
  children: ReactNode

  /**
   * Optional close handler - if provided, shows close button
   */
  onClose?: () => void

  /**
   * Show close button
   */
  closable?: boolean

  /**
   * Custom icon to override default variant icon
   */
  icon?: ReactNode

  /**
   * Additional CSS classes
   */
  className?: string
}

/**
 * Alert component using MC Press brand colors for feedback messages
 *
 * Uses appropriate semantic colors:
 * - Success: MC Green (#A1A88B)
 * - Error: MC Red (#990000)
 * - Warning: MC Orange (#EF9537)
 * - Info: MC Blue (#878DBC)
 *
 * @example
 * ```tsx
 * <Alert variant="success" title="Success!">
 *   Your changes have been saved.
 * </Alert>
 *
 * <Alert variant="error" closable onClose={() => console.log('closed')}>
 *   An error occurred while processing your request.
 * </Alert>
 * ```
 */
export const Alert = ({
  variant,
  title,
  children,
  onClose,
  closable = false,
  icon,
  className = ''
}: AlertProps) => {
  const classNames = [
    styles.alert,
    styles[`variant-${variant}`],
    className
  ].filter(Boolean).join(' ')

  // Default icons for each variant using Unicode symbols for now
  // In production, these would be replaced with react-icons or similar
  const defaultIcons = {
    success: '✓',
    error: '✕',
    warning: '⚠',
    info: 'ℹ'
  }

  const displayIcon = icon ?? defaultIcons[variant]

  return (
    <div className={classNames} role="alert">
      <div className={styles.icon} aria-hidden="true">
        {displayIcon}
      </div>
      <div className={styles.content}>
        {title && <div className={styles.title}>{title}</div>}
        <div className={styles.message}>{children}</div>
      </div>
      {(closable || onClose) && (
        <button
          className={styles.closeButton}
          onClick={onClose}
          aria-label="Close alert"
          type="button"
        >
          ✕
        </button>
      )}
    </div>
  )
}

Alert.displayName = 'Alert'
