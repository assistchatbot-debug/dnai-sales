import React from 'react'

export default function Layout({ children }) {
  return (
    <div className="min-h-screen bg-dark relative overflow-hidden">
      {/* Neural Grid Background */}
      <div className="neural-grid" />
      
      {/* Main Content */}
      <div className="container">
        {/* Header */}
        <div className="text-center mb-12 fade-in">
          <h1 className="text-4xl md:text-5xl font-bold mb-2">
            BizDNAi
          </h1>
          <p className="text-gray-400 text-lg">
            WhatsApp Setup
          </p>
        </div>
        
        {/* Content Card */}
        <div className="w-full max-w-md">
          {children}
        </div>
      </div>
    </div>
  )
}
