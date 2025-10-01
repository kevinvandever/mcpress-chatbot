import styles from './Loading.module.css'

export interface ProgressBarProps {
  /**
   * Progress value (0-100)
   */
  value?: number

  /**
   * Size variant
   */
  size?: 'sm' | 'md' | 'lg'

  /**
   * Color variant
   */
  variant?: 'primary' | 'success' | 'warning' | 'danger'

  /**
   * Show label with percentage
   */
  showLabel?: boolean

  /**
   * Indeterminate mode (no progress value)
   */
  indeterminate?: boolean

  /**
   * Optional label for screen readers
   */
  label?: string
}

/**
 * ProgressBar component for progress indication
 *
 * Shows progress of an operation with optional percentage label
 * Supports indeterminate mode for unknown progress
 *
 * @example
 * ```tsx
 * <ProgressBar value={75} variant="primary" showLabel />
 * <ProgressBar indeterminate variant="success" label="Loading..." />
 * <ProgressBar value={100} variant="success" size="lg" />
 * ```
 */
export const ProgressBar = ({
  value = 0,
  size = 'md',
  variant = 'primary',
  showLabel = false,
  indeterminate = false,
  label
}: ProgressBarProps) => {
  const normalizedValue = Math.min(100, Math.max(0, value))
  const ariaLabel = label || `${normalizedValue}% complete`

  return (
    <div className={styles.progressContainer}>
      {showLabel && !indeterminate && (
        <div className={styles.progressLabel}>{normalizedValue}%</div>
      )}
      <div
        className={`${styles.progressBar} ${styles[`progress-${size}`]}`}
        role="progressbar"
        aria-valuenow={indeterminate ? undefined : normalizedValue}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={ariaLabel}
      >
        <div
          className={`${styles.progressFill} ${styles[`progress-${variant}`]} ${
            indeterminate ? styles.progressIndeterminate : ''
          }`}
          style={indeterminate ? undefined : { width: `${normalizedValue}%` }}
        />
      </div>
    </div>
  )
}
