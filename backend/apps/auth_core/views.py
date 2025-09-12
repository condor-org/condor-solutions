# apps/auth_core/views.py

from rest_framework.generics import CreateAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import viewsets, filters, status
from django.contrib.auth import get_user_model
import time
import requests
from jwt import PyJWKClient, decode as jwt_decode, InvalidTokenError

from .serializers import RegistroSerializer, CustomTokenObtainPairSerializer, UsuarioSerializer
from .models import Usuario

from django.utils.crypto import get_random_string
from django.conf import settings
from .oauth import GoogleOIDCConfig
from .state import sign_state, verify_state

from apps.common.permissions import EsSuperAdmin, EsAdminDeSuCliente

import logging
logger = logging.getLogger(__name__)

User = get_user_model()


# ==========================
# Helpers OAuth/JWT
# ==========================

def _email_domain_ok(email: str) -> bool:
    allowed = getattr(settings, "OAUTH_ALLOWED_EMAIL_DOMAIN", "*")
    if not allowed or allowed == "*":
        return True
    try:
        return email.lower().split("@", 1)[1] == allowed.lower()
    except Exception:
        return False


def _issue_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    access = refresh.access_token
    return str(access), str(refresh)


# ==========================
# Vistas existentes
# ==========================

class RegistroView(CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegistroSerializer
    permission_classes = []  # Público


class MiPerfilView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        logger.debug(f"[YO VIEW] Petición recibida. user.is_authenticated={user.is_authenticated}")
        logger.debug(f"[YO VIEW] user.id={user.id}, email={user.email} si autenticado.")
        logger.debug(f"[YO VIEW] user.token={getattr(user, 'auth_token', 'no_token')}")

        data = {
            "id": user.id,
            "email": user.email,
            "telefono": getattr(user, "telefono", None),
            "tipo_usuario": getattr(user, "tipo_usuario", None),
            "cliente_id": getattr(user, "cliente_id", None),
        }

        logger.debug(f"[YO VIEW] Respondiendo datos: {data}")

        return Response(data)


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        logger.debug(f"[TOKEN REQUEST] Datos recibidos: {request.data}")
        return super().post(request, *args, **kwargs)


class UsuarioViewSet(viewsets.ModelViewSet):
    serializer_class = UsuarioSerializer
    permission_classes = [IsAuthenticated & (EsSuperAdmin | EsAdminDeSuCliente)]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['id', 'email', 'tipo_usuario']

    def get_queryset(self):
        user = self.request.user

        if getattr(user, "tipo_usuario", None) == 'super_admin':
            return Usuario.objects.all()

        if getattr(user, "tipo_usuario", None) == 'admin_cliente' and getattr(user, "cliente", None):
            return Usuario.objects.filter(cliente=user.cliente)

        return Usuario.objects.none()


# ==========================
# OAuth: obtener STATE
# ==========================

class OAuthStateView(APIView):
    permission_classes = []  # público

    def post(self, request):
        """
        Frontend pide un state firmado para iniciar OAuth.
        Body:
          - host: string (obligatorio) ej "padel.cnd-ia.com"
          - invite: string (opcional)
          - return_to: string (opcional) ej "/"
        """
        cfg = GoogleOIDCConfig.from_env()
        errs = cfg.validate()
        if errs:
            logger.warning(f"[OAUTH STATE] config_invalid errs={errs}")
            return Response({"detail": "oauth_config_invalid", "errors": errs}, status=500)

        host = (request.data or {}).get("host")
        invite = (request.data or {}).get("invite")
        return_to = (request.data or {}).get("return_to", "/")
        if not host or not isinstance(host, str):
            return Response({"detail": "host_required"}, status=400)

        nonce = get_random_string(24)
        payload = {"v": 1, "nonce": nonce, "host": host, "return_to": return_to}
        if invite:
            payload["invite"] = invite

        state = sign_state(payload, cfg.state_hmac_secret, ttl_seconds=300)

        # Logs sin PII (hasheamos host y recortamos)
        logger.info(f"[OAUTH STATE] issued host={host} invite={'y' if invite else 'n'}")
        return Response({"state": state, "nonce": nonce}, status=200)


# ==========================
# OAuth: callback REAL (con emisión de JWT)
# ==========================

class OAuthCallbackView(APIView):
    permission_classes = []  # público

    def _issue_tokens(self, user, return_to="/"):
        refresh = RefreshToken.for_user(user)
        return {
            "ok": True,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": user.id,
                "email": user.email,
                "tipo_usuario": getattr(user, "tipo_usuario", None),
                "cliente_id": getattr(user, "cliente_id", None),
            },
            "return_to": return_to,
        }

    def post(self, request):
        cfg = GoogleOIDCConfig.from_env()
        errs = cfg.validate()
        if errs:
            logger.warning(f"[OAUTH CB] config_invalid errs={errs}")
            return Response({"detail": "oauth_config_invalid", "errors": errs}, status=500)

        data = request.data or {}
        provider = data.get("provider")
        code = data.get("code")
        code_verifier = data.get("code_verifier")
        state_raw = data.get("state")

        if provider != "google":
            return Response({"detail": "unsupported_provider"}, status=400)
        if not state_raw:
            return Response({"detail": "state_required"}, status=400)
        if not code or not code_verifier:
            return Response({"detail": "code_and_verifier_required"}, status=400)

        # 1) Validar state
        try:
            state, _ = verify_state(state_raw, cfg.state_hmac_secret)
        except ValueError as ex:
            logger.info(f"[OAUTH CB] state_invalid reason={ex}")
            return Response({"detail": "state_invalid", "reason": str(ex)}, status=400)

        host = state.get("host")
        return_to = state.get("return_to", "/")
        expected_nonce = state.get("nonce")
        invite_payload = state.get("invite")  # aquí podrías pasar cliente_id, rol, etc.

        # 2) Intercambio code->tokens (PKCE)
        token_url = "https://oauth2.googleapis.com/token"
        form = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": cfg.client_id,
            "client_secret": cfg.client_secret,
            "redirect_uri": cfg.redirect_uri,
            "code_verifier": code_verifier,
        }
        t0 = time.time()
        try:
            resp = requests.post(token_url, data=form, timeout=6)
            rt = round(time.time() - t0, 3)
        except requests.RequestException as ex:
            logger.warning(f"[OAUTH CB] token_request_error err={ex}")
            return Response({"detail": "token_request_error"}, status=502)

        if resp.status_code != 200:
            safe_text = resp.text[:300]
            logger.info(f"[OAUTH CB] token_exchange_failed status={resp.status_code} rt={rt}s body~={safe_text!r}")
            return Response({"detail": "token_exchange_failed", "status_code": resp.status_code}, status=400)

        token_body = resp.json()
        id_token = token_body.get("id_token")
        if not id_token:
            logger.info("[OAUTH CB] no_id_token_in_response")
            return Response({"detail": "no_id_token_in_response"}, status=400)

        # 3) Validar ID Token
        try:
            jwks_client = PyJWKClient(cfg.jwks_url)
            signing_key = jwks_client.get_signing_key_from_jwt(id_token).key
            claims = jwt_decode(
                id_token,
                signing_key,
                algorithms=["RS256"],
                audience=cfg.client_id,
                issuer=["https://accounts.google.com", "accounts.google.com"],
                options={"require": ["exp", "iat", "aud", "iss", "sub"]},
            )
        except InvalidTokenError as ex:
            logger.info(f"[OAUTH CB] id_token_invalid reason={ex}")
            return Response({"detail": "id_token_invalid", "reason": str(ex)}, status=400)

        id_nonce = claims.get("nonce")
        if expected_nonce and id_nonce and id_nonce != expected_nonce:
            logger.info(f"[OAUTH CB] nonce_mismatch expected={expected_nonce} got={id_nonce}")
            return Response({"detail": "nonce_mismatch"}, status=400)

        email = claims.get("email")
        email_verified = claims.get("email_verified", False)
        sub = claims.get("sub")

        logger.info(f"[OAUTH CB] ok host={host} invite={'y' if invite_payload else 'n'} email_v={'y' if email_verified else 'n'}")

        # 4) Emitir tokens para usuario existente o auto-provisionar
        try:
            user = User.objects.filter(email=email).first()

            if user:
                # usuario ya existe: emitir tokens
                return Response(self._issue_tokens(user, return_to), status=200)

            # No existe: ¿podemos auto-provisionar?
            auto_prov = bool(getattr(settings, "OAUTH_AUTO_PROVISION", True))
            if not auto_prov:
                # Solo validar y devolver claims (comportamiento anterior)
                return Response({
                    "ok": True,
                    "host": host,
                    "return_to": return_to,
                    "invite_present": bool(invite_payload),
                    "google_claims": {
                        "sub": sub,
                        "email": email,
                        "email_verified": bool(email_verified),
                    },
                    "message": "oauth-callback-validated",
                }, status=200)

            # Resolver cliente y rol
            cliente_id = None
            tipo_usuario = "operador"

            # 4.a) desde invite (si tu FE mete aquí un dict, p.ej. {"cliente_id": 7, "role": "operador"})
            if isinstance(invite_payload, dict):
                cliente_id = invite_payload.get("cliente_id") or invite_payload.get("cliente")
                tipo_usuario = invite_payload.get("role") or tipo_usuario

            # 4.b) desde settings por defecto
            if not cliente_id:
                cliente_id = getattr(settings, "OAUTH_DEFAULT_CLIENT_ID", None)

            # 4.c) primer usuario → super_admin (opcional y solo dev)
            first_super = bool(getattr(settings, "OAUTH_FIRST_USER_SUPERADMIN", False))
            if first_super and not User.objects.exists():
                tipo_usuario = "super_admin"

            # Validación mínima para cumplir tu constraint del modelo
            if tipo_usuario != "super_admin" and not cliente_id:
                # No podemos crear porque tu modelo exige cliente en no-super_admin
                return Response(
                    {"detail": "client_required_for_new_user",
                     "hint": "Define OAUTH_DEFAULT_CLIENT_ID o pasa invite.cliente_id en el state."},
                    status=409
                )

            # Crear usuario
            extra = {"tipo_usuario": tipo_usuario}
            if cliente_id:
                extra["cliente_id"] = cliente_id

            user = User.objects.create_user(
                email=email,
                password=None,  # usable password no es necesario con SSO
                **extra,
            )
            # Opcional: marcar sin password local
            if hasattr(user, "set_unusable_password"):
                user.set_unusable_password()
                user.save(update_fields=["password"])

            return Response(self._issue_tokens(user, return_to), status=200)

        except Exception as ex:
            logger.error(f"[OAUTH CB] unexpected_error email={email}", exc_info=True)
            return Response({"detail": "unexpected_error"}, status=500)