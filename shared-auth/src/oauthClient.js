// shared-auth/oauthClient.js
// Cliente OAuth compartido

import pkce from './pkce';

class OAuthClient {
  constructor() {
    this.clientId = window.RUNTIME_CONFIG?.GOOGLE_CLIENT_ID;
    this.redirectUri = window.RUNTIME_CONFIG?.OAUTH_REDIRECT_URI;
    this.scope = 'openid email profile';
    this.responseType = 'code';
  }

  // Iniciar el flujo de login
  initiateLogin() {
    if (!this.clientId || !this.redirectUri) {
      console.error('OAuth configuration missing');
      return;
    }

    // Generar PKCE parameters
    const codeVerifier = pkce.generateCodeVerifier();
    const codeChallenge = pkce.generateCodeChallenge(codeVerifier);
    
    // Guardar code_verifier para después
    sessionStorage.setItem('oauth_code_verifier', codeVerifier);

    // Construir URL de autorización
    const authUrl = new URL('https://accounts.google.com/o/oauth2/v2/auth');
    authUrl.searchParams.set('client_id', this.clientId);
    authUrl.searchParams.set('redirect_uri', this.redirectUri);
    authUrl.searchParams.set('response_type', this.responseType);
    authUrl.searchParams.set('scope', this.scope);
    authUrl.searchParams.set('code_challenge', codeChallenge);
    authUrl.searchParams.set('code_challenge_method', 'S256');
    authUrl.searchParams.set('access_type', 'offline');
    authUrl.searchParams.set('prompt', 'consent');

    // Redirigir a Google
    window.location.href = authUrl.toString();
  }

  // Manejar callback de OAuth
  async handleCallback() {
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');
    const error = urlParams.get('error');

    if (error) {
      throw new Error(`OAuth error: ${error}`);
    }

    if (!code) {
      throw new Error('No authorization code received');
    }

    // Obtener code_verifier
    const codeVerifier = sessionStorage.getItem('oauth_code_verifier');
    if (!codeVerifier) {
      throw new Error('No code verifier found');
    }

    // Intercambiar código por tokens
    const tokens = await this.exchangeCodeForTokens(code, codeVerifier);
    
    // Limpiar parámetros de URL
    window.history.replaceState({}, document.title, window.location.pathname);
    
    return tokens;
  }

  // Intercambiar código por tokens
  async exchangeCodeForTokens(code, codeVerifier) {
    const response = await fetch('/api/auth/google/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        code,
        code_verifier: codeVerifier,
        redirect_uri: this.redirectUri,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Token exchange failed');
    }

    return await response.json();
  }
}

export default new OAuthClient();
