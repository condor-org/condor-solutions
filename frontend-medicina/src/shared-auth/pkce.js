// shared-auth/pkce.js
// Utilidades PKCE para OAuth

// Generar code verifier
export const generateCodeVerifier = () => {
  const array = new Uint8Array(32);
  crypto.getRandomValues(array);
  return base64URLEncode(array);
};

// Generar code challenge
export const generateCodeChallenge = (codeVerifier) => {
  const encoder = new TextEncoder();
  const data = encoder.encode(codeVerifier);
  const digest = crypto.subtle.digest('SHA-256', data);
  return base64URLEncode(digest);
};

// Codificar en base64 URL-safe
const base64URLEncode = (arrayBuffer) => {
  const bytes = new Uint8Array(arrayBuffer);
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary)
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '');
};

export default {
  generateCodeVerifier,
  generateCodeChallenge,
};
