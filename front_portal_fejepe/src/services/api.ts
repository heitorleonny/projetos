import axios from 'axios';
import { ENV } from '../config/env';
import { supabase } from './supabase';
import { queryClient } from './queryClient';

export const api = axios.create({
    baseURL: ENV.API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

api.interceptors.request.use(
    async (config) => {
        const { data } = await supabase.auth.getSession();
        const token = data.session?.access_token;

        if (token) {
            config.headers = config.headers ?? {};
            config.headers.Authorization = `Bearer ${token}`;
        }

        return config;
    },
    (error) => Promise.reject(error),
);

api.interceptors.response.use(
    (response) => response,
    async (error) => {
        if (error.response?.status === 401) {
            await supabase.auth.signOut();
            queryClient.clear();
            if (window.location.pathname !== '/login') {
                window.location.href = '/login';
            }
        }

        console.error('[API Error]', error.response?.status, error.message);
        return Promise.reject(error);
    },
);
