import React, { useState, useEffect } from 'react'

const CAPTCHA_QUESTIONS = [
  { q: '5 + 3', a: 8 },
  { q: '10 - 4', a: 6 },
  { q: '3 × 4', a: 12 },
  { q: '20 ÷ 4', a: 5 },
  { q: '7 + 2', a: 9 },
  { q: '15 - 8', a: 7 },
  { q: '6 × 2', a: 12 },
  { q: '18 ÷ 3', a: 6 },
]

export default function CaptchaPage({ language, onVerify }) {
  const [currentQuestion, setCurrentQuestion] = useState(null)
  const [answer, setAnswer] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const question = CAPTCHA_QUESTIONS[
      Math.floor(Math.random() * CAPTCHA_QUESTIONS.length)
    ]
    setCurrentQuestion(question)
  }, [])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    const userAnswer = parseInt(answer)
    if (isNaN(userAnswer)) {
      setError(language === 'ru' ? 'Введите число' : 'Please enter a number')
      return
    }

    if (userAnswer === currentQuestion.a) {
      setLoading(true)
      onVerify()
    } else {
      setError(language === 'ru' ? 'Неверный ответ' : 'Incorrect answer')
      setAnswer('')
    }
  }

  const labels = {
    ru: {
      title: 'Проверка человека',
      hint: 'Решите задачу:',
      placeholder: 'Ваш ответ',
      submit: 'Продолжить',
    },
    en: {
      title: 'Verify You\'re Human',
      hint: 'Solve this:',
      placeholder: 'Your answer',
      submit: 'Continue',
    },
  }

  const label = labels[language] || labels.en

  return (
    <div className="card fade-in">
      <h2 className="text-2xl font-bold mb-6 text-center">{label.title}</h2>
      
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="text-center">
          <p className="text-gray-400 mb-2">{label.hint}</p>
          <p className="text-3xl font-bold text-[#a855f7]">
            {currentQuestion?.q}
          </p>
        </div>

        <input
          type="number"
          value={answer}
          onChange={(e) => {
            setAnswer(e.target.value)
            setError('')
          }}
          placeholder={label.placeholder}
          disabled={loading}
          autoFocus
        />

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
