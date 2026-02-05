import React, { useState } from 'react'
import Layout from './components/Layout'
import LanguageSelect from './components/LanguageSelect'
import CaptchaPage from './components/CaptchaPage'
import PhoneInput from './components/PhoneInput'
import Confirmation from './components/Confirmation'
import QRScan from './components/QRScan'
import Success from './components/Success'

export default function App() {
  const [page, setPage] = useState('language')
  const [language, setLanguage] = useState('ru')
  const [company, setCompany] = useState(null)
  const [phone, setPhone] = useState('')
  const [pairingSession, setPairingSession] = useState(null)
  const [accountName, setAccountName] = useState('')

  const handleLanguageSelect = (lang) => {
    setLanguage(lang)
    setPage('captcha')
  }

  const handleCaptchaVerify = () => {
    setPage('phone')
  }

  const handlePhoneFound = (foundCompany, foundPhone) => {
    setCompany(foundCompany)
    setPhone(foundPhone)
    setPage('confirmation')
  }

  const handlePhoneError = (error) => {
    console.error('Phone lookup error:', error)
  }

  const handleConfirmationConfirm = (session) => {
    setPairingSession(session)
    setPage('qr')
  }

  const handleConfirmationCancel = () => {
    setCompany(null)
    setPhone('')
    setPage('phone')
  }

  const handleQRLinked = (result) => {
    setAccountName(result.account_name || `business_company${company.id}`)
    setPage('success')
  }

  const handleQRError = (error) => {
    console.error('QR scan error:', error)
  }

  return (
    <Layout>
      {page === 'language' && (
        <LanguageSelect onSelect={handleLanguageSelect} />
      )}

      {page === 'captcha' && (
        <CaptchaPage language={language} onVerify={handleCaptchaVerify} />
      )}

      {page === 'phone' && (
        <PhoneInput
          language={language}
          onFound={handlePhoneFound}
          onError={handlePhoneError}
        />
      )}

      {page === 'confirmation' && company && (
        <Confirmation
          language={language}
          company={company}
          phone={phone}
          onConfirm={handleConfirmationConfirm}
          onCancel={handleConfirmationCancel}
          onError={handlePhoneError}
        />
      )}

      {page === 'qr' && pairingSession && (
        <QRScan
          language={language}
          pairingId={pairingSession.pairing_id}
          qrCode={pairingSession.qr_code}
          expiresAt={pairingSession.expires_at}
          onLinked={handleQRLinked}
          onError={handleQRError}
        />
      )}

      {page === 'success' && company && (
        <Success
          language={language}
          company={company}
          accountName={accountName}
        />
      )}
    </Layout>
  )
}
