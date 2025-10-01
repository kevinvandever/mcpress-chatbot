import { ReactNode } from 'react'
import styles from './Badge.module.css'

export interface BadgeProps {
  /**
   * Badge content
   */
  children: ReactNode

  /**
   * Badge variant (color)
   */
  variant?: 'primary' | 'success' | 'warning' | 'danger' | 'neutral' | 'info'

  /**
   * Badge size
   */
  size?: 'sm' | 'md' | 'lg'

  /**
   * Badge shape
   */
  shape?: 'rounded' | 'pill'

  /**
   * Outlined style
   */
  outlined?: boolean

  /**
   * Additional CSS class
   */
  className?: string
}

/**
 * Badge component for status indicators and labels
 *
 * Versatile component for displaying status, counts, or labels
 * Supports multiple variants based on MC Press colors
 *
 * @example
 * ```tsx
 * <Badge variant="success">Active</Badge>
 * <Badge variant="danger" outlined>Error</Badge>
 * <Badge variant="primary" size="sm" shape="pill">99+</Badge>
 * <Badge variant="info">New</Badge>
 * ```
 */
export const Badge = ({
  children,
  variant = 'neutral',
  size = 'md',
  shape = 'rounded',
  outlined = false,
  className = ''
}: BadgeProps) => {
  const badgeClasses = [
    styles.badge,
    styles[`variant-${variant}`],
    styles[`size-${size}`],
    styles[`shape-${shape}`],
    outlined && styles.outlined,
    className
  ].filter(Boolean).join(' ')

  return (
    <span className={badgeClasses}>
      {children}
    </span>
  )
}
