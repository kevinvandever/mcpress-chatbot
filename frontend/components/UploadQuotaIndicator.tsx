'use client'

import { useEffect, useState } from 'react'
import { Card, ProgressBar } from './design-system'
import axios from 'axios'
import { API_URL } from '../config/api'

interface QuotaData {
  daily_uploads: number
  max_daily_uploads: number
  daily_storage: number
  max_daily_storage: number
  lifetime_uploads: number
}

interface UploadQuotaIndicatorProps {
  onQuotaUpdate?: (quota: QuotaData) => void
  compact?: boolean
  className?: string
}

/**
 * UploadQuotaIndicator Component
 *
 * Displays user's upload quota status with progress bars
 * Shows daily file uploads and storage usage
 *
 * @example
 * <UploadQuotaIndicator />
 * <UploadQuotaIndicator compact />
 */
export default function UploadQuotaIndicator({
  onQuotaUpdate,
  compact = false,
  className = ''
}: UploadQuotaIndicatorProps) {
  const [quota, setQuota] = useState<QuotaData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchQuota = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await axios.get<QuotaData>(`${API_URL}/api/code/quota`)
      setQuota(response.data)
      onQuotaUpdate?.(response.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load quota')
      console.error('Quota fetch error:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchQuota()
  }, [])

  if (loading) {
    return (
      <Card className={className}>
        <div className="animate-pulse space-y-3">
          <div className="h-4 bg-gray-200 rounded w-3/4"></div>
          <div className="h-2 bg-gray-200 rounded"></div>
          <div className="h-4 bg-gray-200 rounded w-2/3"></div>
          <div className="h-2 bg-gray-200 rounded"></div>
        </div>
      </Card>
    )
  }

  if (error || !quota) {
    return (
      <Card className={className}>
        <div className="text-red-600 text-sm">
          <p className="font-semibold">Failed to load quota</p>
          {error && <p className="text-xs mt-1">{error}</p>}
        </div>
      </Card>
    )
  }

  const filesPercent = (quota.daily_uploads / quota.max_daily_uploads) * 100
  const storagePercent = (quota.daily_storage / quota.max_daily_storage) * 100
  const storageUsedMB = (quota.daily_storage / (1024 * 1024)).toFixed(2)
  const storageMaxMB = (quota.max_daily_storage / (1024 * 1024)).toFixed(0)

  const getVariant = (percent: number): 'success' | 'warning' | 'danger' => {
    if (percent < 70) return 'success'
    if (percent < 90) return 'warning'
    return 'danger'
  }

  if (compact) {
    return (
      <div className={`space-y-2 ${className}`}>
        <div className="text-xs text-gray-600">
          <div className="flex justify-between items-center mb-1">
            <span>Files: {quota.daily_uploads}/{quota.max_daily_uploads} today</span>
            <span className={filesPercent >= 90 ? 'text-red-600 font-semibold' : ''}>
              {filesPercent.toFixed(0)}%
            </span>
          </div>
          <ProgressBar value={filesPercent} variant={getVariant(filesPercent)} size="sm" />
        </div>

        <div className="text-xs text-gray-600">
          <div className="flex justify-between items-center mb-1">
            <span>Storage: {storageUsedMB}/{storageMaxMB} MB</span>
            <span className={storagePercent >= 90 ? 'text-red-600 font-semibold' : ''}>
              {storagePercent.toFixed(0)}%
            </span>
          </div>
          <ProgressBar value={storagePercent} variant={getVariant(storagePercent)} size="sm" />
        </div>
      </div>
    )
  }

  return (
    <Card className={className}>
      <div className="space-y-4">
        <div>
          <h3 className="text-sm font-semibold text-gray-900 mb-1">Daily Upload Quota</h3>
          <p className="text-xs text-gray-500 mb-2">
            Resets daily at midnight
          </p>
        </div>

        {/* Files Quota */}
        <div>
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm text-gray-700">Files Uploaded</span>
            <span className="text-sm font-medium text-gray-900">
              {quota.daily_uploads} / {quota.max_daily_uploads}
            </span>
          </div>
          <ProgressBar value={filesPercent} variant={getVariant(filesPercent)} showLabel />
        </div>

        {/* Storage Quota */}
        <div>
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm text-gray-700">Storage Used</span>
            <span className="text-sm font-medium text-gray-900">
              {storageUsedMB} / {storageMaxMB} MB
            </span>
          </div>
          <ProgressBar value={storagePercent} variant={getVariant(storagePercent)} showLabel />
        </div>

        {/* Lifetime Stats */}
        {quota.lifetime_uploads > 0 && (
          <div className="pt-3 border-t border-gray-200">
            <p className="text-xs text-gray-500">
              Total lifetime uploads: <span className="font-medium text-gray-700">{quota.lifetime_uploads}</span>
            </p>
          </div>
        )}

        {/* Warning if near limit */}
        {(filesPercent >= 90 || storagePercent >= 90) && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3">
            <p className="text-xs text-red-800">
              ⚠️ You're approaching your daily limit. Files will be automatically deleted after 24 hours.
            </p>
          </div>
        )}
      </div>
    </Card>
  )
}
