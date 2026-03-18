export const ENV = {
    API_BASE_URL: import.meta.env.VITE_API_BASE_URL as string,
    USE_MOCK: import.meta.env.VITE_USE_MOCK === 'true',
    SUPABASE_URL: import.meta.env.VITE_SUPABASE_URL as string,
    SUPABASE_ANON_KEY: import.meta.env.VITE_SUPABASE_ANON_KEY as string,
    FEEDBACK_FORM_URL: import.meta.env.VITE_FEEDBACK_FORM_URL as string,
} as const;
