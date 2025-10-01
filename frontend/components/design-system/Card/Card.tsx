import { ReactNode, forwardRef, HTMLAttributes } from 'react'
import styles from './Card.module.css'

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  /**
   * Card content
   */
  children: ReactNode

  /**
   * Card variant affecting visual style
   */
  variant?: 'default' | 'elevated' | 'outlined' | 'interactive'

  /**
   * Adds padding to card content
   */
  padding?: 'none' | 'sm' | 'md' | 'lg'

  /**
   * Adds hover effect for interactive cards
   */
  hoverable?: boolean

  /**
   * Optional card header content
   */
  header?: ReactNode

  /**
   * Optional card footer content
   */
  footer?: ReactNode

  /**
   * Image source for card media section
   */
  image?: string

  /**
   * Alt text for image
   */
  imageAlt?: string

  /**
   * Full width card
   */
  fullWidth?: boolean
}

/**
 * Card component with MC Press design system styling
 *
 * Versatile container component for grouping related content
 * Supports multiple variants, optional header/footer, and media
 *
 * @example
 * ```tsx
 * <Card variant="elevated" padding="md">
 *   <h3>Card Title</h3>
 *   <p>Card content goes here</p>
 * </Card>
 *
 * <Card
 *   variant="interactive"
 *   hoverable
 *   header={<h3>Product Title</h3>}
 *   image="/product.jpg"
 *   imageAlt="Product"
 *   footer={<Button variant="cta">Buy Now</Button>}
 * >
 *   Product description text
 * </Card>
 * ```
 */
export const Card = forwardRef<HTMLDivElement, CardProps>(
  (
    {
      children,
      variant = 'default',
      padding = 'md',
      hoverable = false,
      header,
      footer,
      image,
      imageAlt = '',
      fullWidth = false,
      className = '',
      ...props
    },
    ref
  ) => {
    const cardClasses = [
      styles.card,
      styles[`variant-${variant}`],
      styles[`padding-${padding}`],
      hoverable && styles.hoverable,
      fullWidth && styles.fullWidth,
      className
    ].filter(Boolean).join(' ')

    return (
      <div ref={ref} className={cardClasses} {...props}>
        {image && (
          <div className={styles.media}>
            <img src={image} alt={imageAlt} className={styles.image} />
          </div>
        )}
        {header && <div className={styles.header}>{header}</div>}
        <div className={styles.content}>{children}</div>
        {footer && <div className={styles.footer}>{footer}</div>}
      </div>
    )
  }
)

Card.displayName = 'Card'
