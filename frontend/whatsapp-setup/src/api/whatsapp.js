/**
 * WhatsApp API Client
 */

// Use same domain - backend accessible via bizdnai.com/sales proxy
const API_BASE = '/sales';

// Utility to handle API errors
async function handleApiResponse(response) {
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || error.error || `HTTP ${response.status}`);
  }
  return response.json();
}

/**
 * Lookup company by phone number
 */
export async function lookupCompany(phone) {
  const response = await fetch(`${API_BASE}/api/whatsapp/lookup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phone }),
  });
  return handleApiResponse(response);
}

/**
 * Create pairing session (start WhatsApp pairing)
 */
export async function createPairingSession(companyId, phone, language = 'ru') {
  const response = await fetch(`${API_BASE}/api/whatsapp/pairing/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      company_id: companyId,
      phone,
      language,
    }),
  });
  return handleApiResponse(response);
}

/**
 * Check pairing status (polling)
 */
export async function checkPairingStatus(pairingId) {
  const response = await fetch(
    `${API_BASE}/api/whatsapp/pairing/status?pairing_id=${pairingId}`,
    { method: 'GET' }
  );
  return handleApiResponse(response);
}
