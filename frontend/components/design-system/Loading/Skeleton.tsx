import styles from './Loading.module.css'

export interface SkeletonProps {
  /**
   * Skeleton variant
   */
  variant?: 'text' | 'circular' | 'rectangular'

  /**
   * Width (CSS value)
   */
  width?: string | number

  /**
   * Height (CSS value)
   */
  height?: string | number

  /**
   * Animation enabled
   */
  animation?: boolean

  /**
   * Additional CSS class
   */
  className?: string
}

/**
 * Skeleton component for loading placeholders
 *
 * Provides placeholder UI while content is loading
 * Supports different shapes and optional animation
 *
 * @example
 * ```tsx
 * <Skeleton variant="text" width="100%" height="20px" />
 * <Skeleton variant="circular" width="48px" height="48px" />
 * <Skeleton variant="rectangular" width="100%" height="200px" />
 * ```
 */
export const Skeleton = ({
  variant = 'text',
  width,
  height,
  animation = true,
  className = ''
}: SkeletonProps) => {
  const style: React.CSSProperties = {
    width: typeof width === 'number' ? `${width}px` : width,
    height: typeof height === 'number' ? `${height}px` : height
  }

  return (
    <div
      className={`${styles.skeleton} ${styles[`skeleton-${variant}`]} ${
        animation ? styles.skeletonAnimation : ''
      } ${className}`}
      style={style}
      aria-busy="true"
      aria-live="polite"
    />
  )
}
