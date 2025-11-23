/**
 * Authentication store for managing user state
 *
 * Handles:
 * - JWT token storage (localStorage)
 * - User state
 * - Login/logout
 * - Auth initialization
 */

import { writable, derived, get } from 'svelte/store';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const TOKEN_KEY = 'mentat_auth_token';
const USER_KEY = 'mentat_auth_user';

/**
 * @typedef {Object} User
 * @property {string} id
 * @property {string} email
 * @property {string} display_name
 * @property {string} role
 * @property {string[]} oauth_providers
 * @property {string} created_at
 */

/**
 * @typedef {Object} AuthState
 * @property {boolean} initialized - Whether auth has been checked
 * @property {boolean} loading - Whether auth operation is in progress
 * @property {User|null} user - Current user or null
 * @property {string|null} token - JWT token or null
 * @property {string|null} error - Error message or null
 */

/** @type {AuthState} */
const initialState = {
	initialized: false,
	loading: false,
	user: null,
	token: null,
	error: null
};

// Create the writable store
const { subscribe, set, update } = writable(initialState);

/**
 * Initialize auth from localStorage
 */
async function initialize() {
	update((state) => ({ ...state, loading: true }));

	try {
		const token = localStorage.getItem(TOKEN_KEY);
		const userJson = localStorage.getItem(USER_KEY);

		if (token && userJson) {
			const user = JSON.parse(userJson);

			// Verify token is still valid by calling /auth/me
			const res = await fetch(`${API_URL}/auth/me`, {
				headers: {
					Authorization: `Bearer ${token}`
				}
			});

			if (res.ok) {
				const freshUser = await res.json();
				localStorage.setItem(USER_KEY, JSON.stringify(freshUser));
				set({
					initialized: true,
					loading: false,
					user: freshUser,
					token,
					error: null
				});
				return;
			}

			// Token invalid, clear storage
			localStorage.removeItem(TOKEN_KEY);
			localStorage.removeItem(USER_KEY);
		}

		set({
			initialized: true,
			loading: false,
			user: null,
			token: null,
			error: null
		});
	} catch (err) {
		console.error('Auth initialization error:', err);
		set({
			initialized: true,
			loading: false,
			user: null,
			token: null,
			error: null // Don't show error on init failure
		});
	}
}

/**
 * Check registration status
 * @returns {Promise<{is_open: boolean, requires_invite: boolean, is_first_user: boolean}>}
 */
async function checkRegistration() {
	const res = await fetch(`${API_URL}/auth/check`);
	if (!res.ok) {
		throw new Error('Failed to check registration status');
	}
	return res.json();
}

/**
 * Login with email and password
 * @param {string} email
 * @param {string} password
 * @returns {Promise<User>}
 */
async function login(email, password) {
	update((state) => ({ ...state, loading: true, error: null }));

	try {
		const res = await fetch(`${API_URL}/auth/login`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ email, password })
		});

		if (!res.ok) {
			const error = await res.json().catch(() => ({ detail: 'Login failed' }));
			throw new Error(error.detail || 'Login failed');
		}

		const data = await res.json();

		// Store token and user
		localStorage.setItem(TOKEN_KEY, data.access_token);
		localStorage.setItem(USER_KEY, JSON.stringify(data.user));

		update((state) => ({
			...state,
			loading: false,
			user: data.user,
			token: data.access_token,
			error: null
		}));

		return data.user;
	} catch (err) {
		update((state) => ({
			...state,
			loading: false,
			error: err.message
		}));
		throw err;
	}
}

/**
 * Register a new account
 * @param {string} email
 * @param {string} password
 * @param {string} [displayName]
 * @param {string} [inviteToken]
 * @returns {Promise<User>}
 */
async function register(email, password, displayName = null, inviteToken = null) {
	update((state) => ({ ...state, loading: true, error: null }));

	try {
		const body = { email, password };
		if (displayName) body.display_name = displayName;
		if (inviteToken) body.invite_token = inviteToken;

		const res = await fetch(`${API_URL}/auth/register`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(body)
		});

		if (!res.ok) {
			const error = await res.json().catch(() => ({ detail: 'Registration failed' }));
			throw new Error(error.detail || 'Registration failed');
		}

		const data = await res.json();

		// Store token and user
		localStorage.setItem(TOKEN_KEY, data.access_token);
		localStorage.setItem(USER_KEY, JSON.stringify(data.user));

		update((state) => ({
			...state,
			loading: false,
			user: data.user,
			token: data.access_token,
			error: null
		}));

		return data.user;
	} catch (err) {
		update((state) => ({
			...state,
			loading: false,
			error: err.message
		}));
		throw err;
	}
}

/**
 * Logout and clear storage
 */
function logout() {
	localStorage.removeItem(TOKEN_KEY);
	localStorage.removeItem(USER_KEY);

	set({
		initialized: true,
		loading: false,
		user: null,
		token: null,
		error: null
	});
}

/**
 * Update user profile
 * @param {Object} data - { display_name?, email? }
 * @returns {Promise<User>}
 */
async function updateProfile(data) {
	const state = get(auth);
	if (!state.token) {
		throw new Error('Not authenticated');
	}

	const res = await fetch(`${API_URL}/auth/me`, {
		method: 'PUT',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${state.token}`
		},
		body: JSON.stringify(data)
	});

	if (!res.ok) {
		const error = await res.json().catch(() => ({ detail: 'Update failed' }));
		throw new Error(error.detail || 'Update failed');
	}

	const user = await res.json();
	localStorage.setItem(USER_KEY, JSON.stringify(user));

	update((s) => ({ ...s, user }));

	return user;
}

/**
 * Change password
 * @param {string} currentPassword
 * @param {string} newPassword
 * @returns {Promise<void>}
 */
async function changePassword(currentPassword, newPassword) {
	const state = get(auth);
	if (!state.token) {
		throw new Error('Not authenticated');
	}

	const res = await fetch(`${API_URL}/auth/change-password`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${state.token}`
		},
		body: JSON.stringify({
			current_password: currentPassword,
			new_password: newPassword
		})
	});

	if (!res.ok) {
		const error = await res.json().catch(() => ({ detail: 'Password change failed' }));
		throw new Error(error.detail || 'Password change failed');
	}
}

/**
 * Get current auth token
 * @returns {string|null}
 */
function getToken() {
	return get(auth).token;
}

/**
 * Check if user is admin
 * @returns {boolean}
 */
function isAdmin() {
	const state = get(auth);
	return state.user?.role === 'admin';
}

// Derived stores
const isAuthenticated = derived({ subscribe }, ($auth) => !!$auth.user);
const currentUser = derived({ subscribe }, ($auth) => $auth.user);
const isLoading = derived({ subscribe }, ($auth) => $auth.loading);
const authError = derived({ subscribe }, ($auth) => $auth.error);

// Export store with methods
export const auth = {
	subscribe,
	initialize,
	checkRegistration,
	login,
	register,
	logout,
	updateProfile,
	changePassword,
	getToken,
	isAdmin
};

// Export derived stores
export { isAuthenticated, currentUser, isLoading, authError };

// Export utility to get token for API calls
export function getAuthHeaders() {
	const token = get(auth).token;
	if (!token) return {};
	return {
		Authorization: `Bearer ${token}`
	};
}
