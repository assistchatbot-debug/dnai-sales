import React from 'react'

export default function Success({ language, company, accountName }) {
  const labels = {
    ru: {
      title: '✅ Успешно!',
      text: 'WhatsApp Business успешно подключен',
      details: {
        company: 'Компания:',
        account: 'Аккаунт:',
      },
      button: 'Закрыть',
    },
    en: {
      title: '✅ Success!',
      text: 'WhatsApp Business has been successfully connected',
      details: {
        company: 'Company:',
        account: 'Account:',
      },
      button: 'Close',
    },
  }

  const label = labels[language] || labels.en

  return (
    <div className="card fade-in">
      <h2 className="text-3xl font-bold mb-2 text-center text-[#a855f7]">
        {label.title}
      </h2>
      
      <div className="space-y-6">
        <p className="text-center text-gray-300">
          {label.text}
        </p>

        <div className="bg-white/5 rounded-lg p-4 space-y-3">
          <div>
            <p className="text-xs text-gray-500 uppercase">{label.details.company}</p>
            <p className="text-lg font-semibold">{company.name}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase">{label.details.account}</p>
            <p className="text-lg font-semibold text-[#a855f7]">{accountName}</p>
          </div>
        </div>

        <button
          onClick={() => window.close()}
          className="btn btn-primary w-full"
        >
          {label.button}
        </button>
      </div>
    </div>
  )
}
