import React from 'react'

const LANGUAGES = [
  { code: 'ru', label: 'Русский' },
  { code: 'en', label: 'English' },
  { code: 'kk', label: 'Қазақша' },
  { code: 'ky', label: 'Кыргызча' },
  { code: 'uz', label: "O'zbek" },
]

export default function LanguageSelect({ onSelect }) {
  return (
    <div className="card fade-in">
      <h2 className="text-2xl font-bold mb-6 text-center">
        Choose Language / Выберите язык
      </h2>
      
      <div className="space-y-3">
        {LANGUAGES.map((lang) => (
          <button
            key={lang.code}
            onClick={() => onSelect(lang.code)}
            className="btn btn-secondary w-full text-left"
          >
            {lang.label}
          </button>
        ))}
      </div>
    </div>
  )
}
