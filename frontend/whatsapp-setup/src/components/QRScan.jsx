import React, { useState, useEffect } from 'react'
import { checkPairingStatus } from '../api/whatsapp'

export default function QRScan({ language, pairingId, qrCode, expiresAt, onLinked, onError }) {
  const [status, setStatus] = useState('pending')
  const [timeLeft, setTimeLeft] = useState(300)
  const [error, setError] = useState('')
  const [isPolling, setIsPolling] = useState(true)

  const labels = {
    ru: {
      title: 'Сканируйте QR код',
      steps: [
        '1. Откройте WhatsApp Business',
        '2. Перейдите в Настройки → Связанные аккаунты',
        '3. Нажмите "Добавить аккаунт"',
        '4. Отсканируйте QR код',
      ],
      waiting: 'Ожидание сканирования...',
      open: 'Открыть WhatsApp',
      error: 'Ошибка сканирования',
      expired: 'QR код истек, начните заново',
      errors: {
        fetch: 'Ошибка проверки статуса',
      },
    },
    en: {
      title: 'Scan QR Code',
      steps: [
        '1. Open WhatsApp Business',
        '2. Go to Settings → Linked Accounts',
        '3. Tap "Add Account"',
        '4. Scan the QR code',
      ],
      waiting: 'Waiting for scan...',
      open: 'Open WhatsApp',
      error: 'Scanning error',
      expired: 'QR expired, start over',
      errors: {
        fetch: 'Error checking status',
      },
    },
  }

  const label = labels[language] || labels.en

  useEffect(() => {
    if (!isPolling) return

    const pollInterval = setInterval(async () => {
      try {
        const result = await checkPairingStatus(pairingId)
        
        if (result.status === 'linked') {
          setStatus('linked')
          setIsPolling(false)
          onLinked?.(result)
        } else if (result.status === 'failed') {
          setStatus('failed')
          setError(label.error)
          setIsPolling(false)
        } else if (result.status === 'expired') {
          setStatus('expired')
          setError(label.expired)
          setIsPolling(false)
        }
      } catch (err) {
        console.error(err)
        setError(label.errors.fetch)
      }
    }, 2000)

    return () => clearInterval(pollInterval)
  }, [pairingId, isPolling, onLinked, label])

  useEffect(() => {
    const timerInterval = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          setStatus('expired')
          setIsPolling(false)
          return 0
        }
        return prev - 1
      })
    }, 1000)

    return () => clearInterval(timerInterval)
  }, [])

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const handleOpenWhatsApp = () => {
    // Deep link to WhatsApp Business settings
    window.open('whatsapp://wa.me/?text=', '_blank')
  }

  return (
    <div className="card fade-in">
      <h2 className="text-2xl font-bold mb-6 text-center">{label.title}</h2>
      
      <div className="space-y-6">
        {/* QR Code */}
        {qrCode && (
          <div className="flex justify-center">
            <img
              src={qrCode}
              alt="WhatsApp QR Code"
              className="w-48 h-48 border-2 border-[#7c3aed] rounded-lg"
            />
          </div>
        )}

        {/* Status */}
        <div className="text-center">
          <p className="text-gray-400 mb-2">
            {status === 'pending' ? label.waiting : status}
          </p>
          <p className="text-2xl font-bold text-[#a855f7]">
            {formatTime(timeLeft)}
          </p>
        </div>

        {/* Instructions */}
        <div className="bg-white/5 rounded-lg p-4 space-y-2">
          {label.steps.map((step, idx) => (
            <p key={idx} className="text-sm text-gray-300">
              {step}
            </p>
          ))}
        </div>

        {error && (
          <p className="text-red-400 text-sm text-center">{error}</p>
        )}

        {/* Buttons */}
        <button
          onClick={handleOpenWhatsApp}
          disabled={status !== 'pending'}
          className="btn btn-primary w-full"
        >
          {label.open}
        </button>
      </div>
    </div>
  )
}
