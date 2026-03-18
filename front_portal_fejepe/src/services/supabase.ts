import { createClient } from '@supabase/supabase-js';
import { ENV } from '../config/env';

if (!ENV.SUPABASE_URL || !ENV.SUPABASE_ANON_KEY) {
    // Keep startup alive for local dev, but auth actions will fail until env is set.
    console.warn('[Auth] Missing VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY.');
}

export const supabase = createClient(ENV.SUPABASE_URL || '', ENV.SUPABASE_ANON_KEY || '');
