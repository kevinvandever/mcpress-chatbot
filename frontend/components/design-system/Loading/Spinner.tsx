import styles from './Loading.module.css'

export interface SpinnerProps {
  /**
   * Spinner size
   */
  size?: 'sm' | 'md' | 'lg' | 'xl'

  /**
   * Spinner color variant
   */
  variant?: 'primary' | 'secondary' | 'white'

  /**
   * Optional label for screen readers
   */
  label?: string
}

/**
 * Spinner component for loading states
 *
 * Animated circular spinner using MC Press colors
 * Accessible with proper ARIA attributes
 *
 * @example
 * ```tsx
 * <Spinner size="md" variant="primary" />
 * <Spinner size="lg" variant="white" label="Loading content..." />
 * ```
 */
export const Spinner = ({ size = 'md', variant = 'primary', label = 'Loading...' }: SpinnerProps) => {
  return (
    <div
      className={`${styles.spinner} ${styles[`spinner-${size}`]} ${styles[`spinner-${variant}`]}`}
      role="status"
      aria-label={label}
    >
      <span className={styles.visuallyHidden}>{label}</span>
    </div>
  )
}
