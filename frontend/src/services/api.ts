import axios from 'axios';

const api = axios.create({
    baseURL: `http://${window.location.hostname}:5000`, // Dynamic IP for remote access
    withCredentials: true,
});

// Interceptor para tratar erros globais (como 401 Unauthorized)
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response && error.response.status === 401) {
            localStorage.removeItem('token');
            localStorage.removeItem('username');
            if (window.location.pathname !== '/login') {
                window.location.href = '/login';
            }
        }
        return Promise.reject(error);
    }
);

export default api;
