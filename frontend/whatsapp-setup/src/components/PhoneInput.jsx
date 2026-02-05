import React, { useState } from 'react'
import { lookupCompany } from '../api/whatsapp'

export default function PhoneInput({ language, onFound, onError }) {
  const [phone, setPhone] = useState('+7')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const labels = {
    ru: {
      title: 'Введите номер WhatsApp',
      placeholder: '+7 (XXX) XXX-XX-XX',
      note: 'Номер должен быть зарегистрирован в системе',
      submit: 'Продолжить',
      errors: {
        invalid: 'Неверный формат номера',
        not_found: 'Номер не найден в системе',
        server: 'Ошибка сервера',
      },
    },
    en: {
      title: 'Enter WhatsApp Number',
      placeholder: '+7 (XXX) XXX-XX-XX',
      note: 'Number must be registered in the system',
      submit: 'Continue',
      errors: {
        invalid: 'Invalid phone format',
        not_found: 'Number not found in system',
        server: 'Server error',
      },
    },
  }

  const label = labels[language] || labels.en

  const formatPhoneDisplay = (value) => {
    const cleaned = value.replace(/\D/g, '')
    if (cleaned.length <= 1) return '+7'
    if (cleaned.length <= 3) return `+${cleaned.slice(0, 1)} (${cleaned.slice(1)}`
    if (cleaned.length <= 6) return `+${cleaned.slice(0, 1)} (${cleaned.slice(1, 4)}) ${cleaned.slice(4)}`
    return `+${cleaned.slice(0, 1)} (${cleaned.slice(1, 4)}) ${cleaned.slice(4, 7)}-${cleaned.slice(7, 9)}-${cleaned.slice(9, 11)}`
  }

  const getPhoneForApi = (displayValue) => {
    return '+' + displayValue.replace(/\D/g, '')
  }

  const handleChange = (e) => {
    const value = e.target.value
    setPhone(formatPhoneDisplay(value))
    setError('')
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    const phoneForApi = getPhoneForApi(phone)
    if (phoneForApi.length !== 12) {
      setError(label.errors.invalid)
      return
    }

    setLoading(true)
    try {
      const result = await lookupCompany(phoneForApi)
      if (result.found) {
        onFound(result.company, phoneForApi)
      } else {
        setError(label.errors.not_found)
      }
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
      
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <input
            type="tel"
            value={phone}
            onChange={handleChange}
            placeholder={label.placeholder}
            disabled={loading}
            maxLength="20"
            autoFocus
          />
          <p className="text-xs text-gray-500 mt-2">{label.note}</p>
        </div>

        {error && <p className="text-red-400 text-sm text-center">{error}</p>}

        <button
          type="submit"
          disabled={loading}
          className="btn btn-primary w-full"
        >
          {loading ? <span className="spinner" /> : label.submit}
        </button>
      </form>
    </div>
  )
}
