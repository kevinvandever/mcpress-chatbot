'use client'

import { ReactNode, useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import styles from './Modal.module.css'

export interface ModalProps {
  /**
   * Whether the modal is open
   */
  isOpen: boolean

  /**
   * Callback when modal should close
   */
  onClose: () => void

  /**
   * Modal title
   */
  title?: string

  /**
   * Modal content
   */
  children: ReactNode

  /**
   * Modal size variant
   */
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full'

  /**
   * Close on backdrop click
   */
  closeOnBackdropClick?: boolean

  /**
   * Close on escape key
   */
  closeOnEscape?: boolean

  /**
   * Show close button
   */
  showCloseButton?: boolean

  /**
   * Optional footer content
   */
  footer?: ReactNode
}

/**
 * Modal component with MC Press design system styling
 *
 * Accessible modal dialog with focus trap and keyboard navigation
 * Uses React Portal to render outside the normal DOM hierarchy
 *
 * @example
 * ```tsx
 * const [isOpen, setIsOpen] = useState(false)
 *
 * <Modal
 *   isOpen={isOpen}
 *   onClose={() => setIsOpen(false)}
 *   title="Confirm Action"
 *   footer={
 *     <>
 *       <Button variant="secondary" onClick={() => setIsOpen(false)}>Cancel</Button>
 *       <Button variant="primary" onClick={handleConfirm}>Confirm</Button>
 *     </>
 *   }
 * >
 *   Are you sure you want to proceed?
 * </Modal>
 * ```
 */
export const Modal = ({
  isOpen,
  onClose,
  title,
  children,
  size = 'md',
  closeOnBackdropClick = true,
  closeOnEscape = true,
  showCloseButton = true,
  footer
}: ModalProps) => {
  const modalRef = useRef<HTMLDivElement>(null)
  const previousActiveElement = useRef<HTMLElement | null>(null)

  // Handle escape key
  useEffect(() => {
    if (!isOpen || !closeOnEscape) return

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose()
      }
    }

    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [isOpen, closeOnEscape, onClose])

  // Handle focus trap
  useEffect(() => {
    if (!isOpen) return

    // Store previously focused element
    previousActiveElement.current = document.activeElement as HTMLElement

    // Focus the modal
    modalRef.current?.focus()

    // Prevent body scroll
    document.body.style.overflow = 'hidden'

    return () => {
      // Restore body scroll
      document.body.style.overflow = ''

      // Restore focus to previously focused element
      previousActiveElement.current?.focus()
    }
  }, [isOpen])

  // Handle focus trap within modal
  useEffect(() => {
    if (!isOpen || !modalRef.current) return

    const modal = modalRef.current
    const focusableElements = modal.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    )
    const firstElement = focusableElements[0]
    const lastElement = focusableElements[focusableElements.length - 1]

    const handleTab = (event: KeyboardEvent) => {
      if (event.key !== 'Tab') return

      if (event.shiftKey) {
        // Shift + Tab
        if (document.activeElement === firstElement) {
          event.preventDefault()
          lastElement?.focus()
        }
      } else {
        // Tab
        if (document.activeElement === lastElement) {
          event.preventDefault()
          firstElement?.focus()
        }
      }
    }

    modal.addEventListener('keydown', handleTab)
    return () => modal.removeEventListener('keydown', handleTab)
  }, [isOpen])

  const handleBackdropClick = (event: React.MouseEvent<HTMLDivElement>) => {
    if (closeOnBackdropClick && event.target === event.currentTarget) {
      onClose()
    }
  }

  if (!isOpen) return null

  const modalContent = (
    <div className={styles.backdrop} onClick={handleBackdropClick}>
      <div
        ref={modalRef}
        className={`${styles.modal} ${styles[`size-${size}`]}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? 'modal-title' : undefined}
        tabIndex={-1}
      >
        {(title || showCloseButton) && (
          <div className={styles.header}>
            {title && (
              <h2 id="modal-title" className={styles.title}>
                {title}
              </h2>
            )}
            {showCloseButton && (
              <button
                type="button"
                className={styles.closeButton}
                onClick={onClose}
                aria-label="Close modal"
              >
                ×
              </button>
            )}
          </div>
        )}
        <div className={styles.content}>{children}</div>
        {footer && <div className={styles.footer}>{footer}</div>}
      </div>
    </div>
  )

  // Use portal to render modal at document.body level
  if (typeof document !== 'undefined') {
    return createPortal(modalContent, document.body)
  }

  return null
}
