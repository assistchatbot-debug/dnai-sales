import React, { useState } from 'react'
import { createPairingSession } from '../api/whatsapp'

export default function Confirmation({ language, company, phone, onConfirm, onCancel, onError }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const labels = {
    ru: {
      title: 'Подтверждение',
      text: 'Вы подключаете WhatsApp к компании:',
      button: 'Продолжить к QR',
      cancel: 'Изменить номер',
      errors: {
        server: 'Ошибка при создании сеанса',
      },
    },
    en: {
      title: 'Confirmation',
      text: 'You are connecting WhatsApp to:',
      button: 'Continue to QR',
      cancel: 'Change Number',
      errors: {
        server: 'Error creating session',
      },
    },
  }

  const label = labels[language] || labels.en

  const handleConfirm = async () => {
    setError('')
    setLoading(true)

    try {
      const result = await createPairingSession(company.id, phone, language)
      onConfirm(result)
    } catch (err) {
      console.error(err)
      setError(label.errors.server)
      onError?.(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="card fade-in">
      <h2 className="text-2xl font-bold mb-6 text-center">{label.title}</h2>
      
      <div className="space-y-6">
        <div>
          <p className="text-gray-400 mb-3">{label.text}</p>
          <div className="bg-white/5 border border-white/10 rounded-lg p-4">
            <p className="text-lg font-semibold">{company.name}</p>
            <p className="text-sm text-gray-400 mt-1">{company.email}</p>
          </div>
        </div>

        {error && <p className="text-red-400 text-sm text-center">{error}</p>}

        <div className="space-y-3">
          <button
            onClick={handleConfirm}
            disabled={loading}
            className="btn btn-primary w-full"
          >
            {loading ? <span className="spinner" /> : label.button}
          </button>
          <button
            onClick={onCancel}
            disabled={loading}
            className="btn btn-secondary w-full"
          >
            {label.cancel}
          </button>
        </div>
      </div>
    </div>
  )
}
