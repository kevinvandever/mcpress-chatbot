'use client'

import { Badge } from './design-system'

interface FileTypeIndicatorProps {
  fileName: string
  className?: string
}

const FILE_TYPE_CONFIG: Record<string, { label: string; color: 'neutral' | 'primary' | 'success' | 'warning' | 'danger' | 'info'; icon: string }> = {
  '.rpg': { label: 'RPG', color: 'primary', icon: '📝' },
  '.rpgle': { label: 'RPGLE', color: 'primary', icon: '📝' },
  '.sqlrpgle': { label: 'SQLRPGLE', color: 'info', icon: '🗄️' },
  '.cl': { label: 'CL', color: 'success', icon: '⚙️' },
  '.clle': { label: 'CLLE', color: 'success', icon: '⚙️' },
  '.sql': { label: 'SQL', color: 'info', icon: '🗄️' },
  '.txt': { label: 'TXT', color: 'neutral', icon: '📄' },
}

/**
 * FileTypeIndicator Component
 *
 * Displays a badge with icon and label for different IBM i code file types
 *
 * @example
 * <FileTypeIndicator fileName="PAYROLL.rpgle" />
 * <FileTypeIndicator fileName="BACKUP.cl" />
 */
export default function FileTypeIndicator({ fileName, className = '' }: FileTypeIndicatorProps) {
  // Extract file extension
  const extension = fileName.toLowerCase().match(/\.(rpg|rpgle|sqlrpgle|cl|clle|sql|txt)$/)?.[0] || '.txt'
  const config = FILE_TYPE_CONFIG[extension] || FILE_TYPE_CONFIG['.txt']

  return (
    <Badge variant={config.color} className={className}>
      <span className="mr-1">{config.icon}</span>
      {config.label}
    </Badge>
  )
}
