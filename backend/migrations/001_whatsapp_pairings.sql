-- Migration: WhatsApp Pairings Table
-- Version: 001
-- Date: 2026-02-05
-- Purpose: Store WhatsApp pairing sessions

CREATE TABLE IF NOT EXISTS whatsapp_pairings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id INTEGER NOT NULL UNIQUE,
  phone VARCHAR(20) NOT NULL,
  pairing_code VARCHAR(20),
  qr_code TEXT NOT NULL,
  status VARCHAR(20) DEFAULT 'pending',
  account_name VARCHAR(100),
  linked_at TIMESTAMP WITH TIME ZONE,
  expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
  language VARCHAR(5) DEFAULT 'ru',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_company_id_whatsapp ON whatsapp_pairings(company_id);
CREATE INDEX IF NOT EXISTS idx_status_whatsapp ON whatsapp_pairings(status);
CREATE INDEX IF NOT EXISTS idx_phone_whatsapp ON whatsapp_pairings(phone);
CREATE INDEX IF NOT EXISTS idx_expires_whatsapp ON whatsapp_pairings(expires_at);

-- Function to update companies.whatsapp when pairing linked
CREATE OR REPLACE FUNCTION update_company_whatsapp()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.status = 'linked' AND NEW.phone IS NOT NULL THEN
    UPDATE companies SET whatsapp = NEW.phone WHERE id = NEW.company_id;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to execute function on update
DROP TRIGGER IF EXISTS trigger_update_company_whatsapp ON whatsapp_pairings;
CREATE TRIGGER trigger_update_company_whatsapp
AFTER UPDATE ON whatsapp_pairings
FOR EACH ROW
EXECUTE FUNCTION update_company_whatsapp();
