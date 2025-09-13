# apps/auth_core/views.py
from rest_framework.generics import CreateAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import viewsets, filters, status

from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string
from django.conf import settings

import time
import requests
import logging
from jwt import PyJWKClient, decode as jwt_decode, InvalidTokenError

from .serializers import RegistroSerializer, CustomTokenObtainPairSerializer, UsuarioSerializer
from .state import sign_state, verify_state
from .oauth import GoogleOIDCConfig
from .models import Usuario

from apps.common.permissions import EsSuperAdmin, EsAdminDeSuCliente
from apps.clientes_core.models import ClienteDominio

logger = logging.getLogger(__name__)
User = get_user_model()

from urllib.parse import quote







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

def _issue_tokens_for_user(user, return_to="/"):
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(user)
    access = refresh.access_token
    access["email"] = user.email
    access["tipo_usuario"] = user.tipo_usuario
    access["cliente_id"] = user.cliente_id
    return {
        "ok": True,
        "access": str(access),
        "refresh": str(refresh),
        "user": {
            "id": user.id,
            "email": user.email,
            "tipo_usuario": user.tipo_usuario,
            "cliente_id": user.cliente_id,
        },
        "return_to": return_to,
    }
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
        data = {
            "id": user.id,
            "email": user.email,
            "telefono": getattr(user, "telefono", None),
            "tipo_usuario": getattr(user, "tipo_usuario", None),
            "cliente_id": getattr(user, "cliente_id", None),
        }
        logger.debug(f"[YO VIEW] user_id={user.id} cliente_id={data['cliente_id']}")
        return Response(data)

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        logger.debug(f"[TOKEN REQUEST] body_keys={list((request.data or {}).keys())}")
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
          - invite: string (opcional)  (para flujos especiales)
          - return_to: string (opcional) ej "/"
        """
        cfg = GoogleOIDCConfig.from_env()
        errs = cfg.validate()
        if errs:
            logger.warning(f"[OAUTH STATE] config_invalid errs={errs}")
            return Response({"detail": "oauth_config_invalid", "errors": errs}, status=500)

        body = request.data or {}
        host = body.get("host")
        invite = body.get("invite")
        return_to = body.get("return_to", "/")

        if not host or not isinstance(host, str):
            return Response({"detail": "host_required"}, status=400)

        # Resolver cliente por host
        strict = getattr(settings, "TENANT_STRICT_HOST", True)
        dom = ClienteDominio.objects.select_related("cliente").filter(hostname=host, activo=True).first()
        if not dom and strict:
            logger.info(f"[OAUTH STATE] unknown_host host={host}")
            return Response({"detail": "unknown_host"}, status=400)

        cliente_id = dom.cliente_id if dom else getattr(settings, "TENANT_DEFAULT_CLIENTE_ID", None)

        nonce = get_random_string(24)
        payload = {
            "v": 1,
            "nonce": nonce,
            "host": host,
            "return_to": return_to,
            "cliente_id": cliente_id,
        }
        if invite:
            payload["invite"] = invite

        state = sign_state(payload, cfg.state_hmac_secret, ttl_seconds=300)
        logger.info(f"[OAUTH STATE] issued host={host} cliente_id={cliente_id} invite={'y' if invite else 'n'}")
        return Response({"state": state, "nonce": nonce}, status=200)

# ==========================
# OAuth: callback REAL (con emisión de JWT)
# ==========================

class OAuthCallbackView(APIView):
    permission_classes = []  # público

    # --- Google llega por GET con ?code=&state= ---
    def get(self, request):
        cfg = GoogleOIDCConfig.from_env()
        errs = cfg.validate()
        if errs:
            logger.warning(f"[OAUTH CB][GET] config_invalid errs={errs}")
            return Response({"detail": "oauth_config_invalid", "errors": errs}, status=500)

        code = (request.query_params.get("code") or "").strip()
        state_raw = (request.query_params.get("state") or "").strip()
        if not code or not state_raw:
            return Response({"detail": "missing code/state"}, status=400)

        # Validamos el state para extraer el host de retorno
        try:
            state, _ = verify_state(state_raw, cfg.state_hmac_secret)
        except ValueError as ex:
            logger.info(f"[OAUTH CB][GET] state_invalid reason={ex}")
            return Response({"detail": "state_invalid", "reason": str(ex)}, status=400)

        host = (state or {}).get("host")
        if not host:
            logger.info("[OAUTH CB][GET] missing_host_in_state")
            return Response({"detail": "cliente_not_resolved"}, status=400)

        # Redirigir a la SPA con SLASH para que NO matchee el location exacto del BE
        redirect_url = f"https://{host}/oauth/google/callback/?code={quote(code)}&state={quote(state_raw)}"
        logger.info(f"[OAUTH CB][GET] redirecting_to_fe host={host}")
        return Response(status=302, headers={"Location": redirect_url})

    # --- Callback vía POST desde la SPA con provider/code_verifier ---
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

        cliente_id_state = state.get("cliente_id")
        if cliente_id_state is not None:
            try:
                cliente_id_state = int(cliente_id_state)
            except Exception:
                logger.info("[OAUTH CB] cliente_id_in_state_not_int value=%r", cliente_id_state)
                return Response({"detail": "cliente_not_resolved"}, status=400)

        if cliente_id_state is None and getattr(settings, "TENANT_STRICT_HOST", True):
            logger.info("[OAUTH CB] missing_cliente_in_state host=%s", host)
            return Response({"detail": "cliente_not_resolved"}, status=400)

        # 1.b) Invite opcional
        invite_raw = state.get("invite")
        inv_payload = None
        invited_admin = False
        invited_email = None
        if invite_raw:
            try:
                inv_payload, _ = verify_state(invite_raw, settings.SECRET_KEY)
            except ValueError as ex:
                logger.info(f"[OAUTH CB] invite_invalid reason={ex}")
                return Response({"detail": "invite_invalid"}, status=400)

            if inv_payload.get("intent") != "invite":
                return Response({"detail": "invite_invalid_intent"}, status=400)

            inv_cliente_id = inv_payload.get("cliente_id")
            if inv_cliente_id is not None:
                try:
                    inv_cliente_id = int(inv_cliente_id)
                except Exception:
                    return Response({"detail": "invite_invalid_cliente"}, status=400)

            if inv_cliente_id and cliente_id_state and inv_cliente_id != cliente_id_state:
                return Response({"detail": "invite_tenant_mismatch"}, status=403)

            invited_admin = (inv_payload.get("role") == "admin_cliente")
            invited_email = (inv_payload.get("email") or None)

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
            resp = requests.post(token_url, data=form, timeout=8)
            rt = round(time.time() - t0, 3)
        except requests.RequestException as ex:
            logger.warning(f"[OAUTH CB] token_request_error err={ex}")
            return Response({"detail": "token_request_error"}, status=502)

        if resp.status_code != 200:
            logger.info(f"[OAUTH CB] token_exchange_failed status={resp.status_code} rt={rt}s body~={resp.text[:300]!r}")
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

        if not email or not _email_domain_ok(email):
            logger.info(f"[OAUTH CB] email_domain_blocked email_mask={email[:2]}***")
            return Response({"detail": "email_domain_not_allowed"}, status=403)
        if getattr(settings, "OAUTH_REQUIRE_EMAIL_VERIFIED", True) and not email_verified:
            logger.info("[OAUTH CB] email_not_verified")
            return Response({"detail": "email_not_verified"}, status=403)

        if invited_email and invited_email.lower() != (email or "").lower():
            return Response({"detail": "invite_email_mismatch"}, status=403)

        logger.info(
            f"[OAUTH CB] ok host={host} cliente_id={cliente_id_state} invite={'y' if invite_raw else 'n'} "
            f"promote={'y' if invited_admin else 'n'} email_v={'y' if email_verified else 'n'}"
        )

        # 4) Usuario existente / onboarding
        try:
            user = User.objects.filter(email=email).first()
            if user:
                if getattr(user, "tipo_usuario", "") != "super_admin":
                    if cliente_id_state and user.cliente_id != cliente_id_state:
                        logger.info(
                            "[OAUTH CB] user_tenant_mismatch user_cliente=%s state_cliente=%s email_mask=%s***",
                            user.cliente_id, cliente_id_state, email[:2]
                        )
                        return Response({"detail": "tenant_mismatch"}, status=403)

                updates = {}
                if not getattr(user, "oauth_provider", None):
                    updates["oauth_provider"] = "google"
                if not getattr(user, "oauth_uid", None):
                    updates["oauth_uid"] = sub
                if invited_admin and user.tipo_usuario not in ("super_admin", "admin_cliente"):
                    updates["tipo_usuario"] = "admin_cliente"
                    logger.info(f"[OAUTH CB] promoting_user_to_admin user_id={user.id} cliente_id={user.cliente_id}")
                if updates:
                    for k, v in updates.items():
                        setattr(user, k, v)
                    user.save(update_fields=list(updates.keys()))

                return Response(_issue_tokens_for_user(user, return_to), status=200)

            pending_payload = {
                "v": 1,
                "intent": "onboard",
                "host": host,
                "cliente_id": cliente_id_state,
                "sub": sub,
                "email": email,
            }
            if invite_raw:
                pending_payload["invite"] = invite_raw

            pending_token = sign_state(pending_payload, settings.SECRET_KEY, ttl_seconds=900)

            return Response({
                "needs_onboarding": True,
                "pending_token": pending_token,
                "prefill": {
                    "email": email,
                    "given_name": claims.get("given_name"),
                    "family_name": claims.get("family_name"),
                    "picture": claims.get("picture"),
                },
                "return_to": "/signup"
            }, status=200)

        except Exception:
            logger.error(f"[OAUTH CB] unexpected_error email_mask={str(email)[:2]}***", exc_info=True)
            return Response({"detail": "unexpected_error"}, status=500)

# ==========================
# Onboarding (opcional, si OAUTH_AUTO_PROVISION=False)
# ==========================

class OnboardView(APIView):
    permission_classes = []  # público

    def post(self, request):
        body = request.data or {}
        pending_token = body.get("pending_token")
        if not pending_token:
            return Response({"detail": "pending_token_required"}, status=400)

        try:
            payload, _ = verify_state(pending_token, settings.SECRET_KEY)
        except ValueError as ex:
            logger.info(f"[ONBOARD] pending_invalid reason={ex}")
            return Response({"detail": "pending_invalid", "reason": str(ex)}, status=400)

        if payload.get("intent") != "onboard":
            return Response({"detail": "pending_intent_invalid"}, status=400)

        cliente_id = payload.get("cliente_id")
        email = payload.get("email")
        sub = payload.get("sub")
        invite_raw = payload.get("invite")  # <--- viene del callback
        if not (cliente_id and email and sub):
            return Response({"detail": "pending_token_incomplete"}, status=400)

        if not body.get("acepta_tos"):
            return Response({"detail": "tos_required"}, status=400)
        nombre = (body.get("nombre") or "").strip()
        apellido = (body.get("apellido") or "").strip()
        if not nombre or not apellido:
            return Response({"detail": "nombre_apellido_required"}, status=400)

        # Rol por defecto
        new_user_role = "usuario_final"

        # Si hay invite, validarlo y, si corresponde, setear admin
        if invite_raw:
            try:
                inv_payload, _ = verify_state(invite_raw, settings.SECRET_KEY)
                if inv_payload.get("intent") != "invite":
                    return Response({"detail": "invite_invalid_intent"}, status=400)
                inv_cliente_id = inv_payload.get("cliente_id")
                if inv_cliente_id and int(inv_cliente_id) != int(cliente_id):
                    return Response({"detail": "invite_tenant_mismatch"}, status=403)
                invited_email = inv_payload.get("email")
                if invited_email and invited_email.lower() != email.lower():
                    return Response({"detail": "invite_email_mismatch"}, status=403)
                if (inv_payload.get("role") or "") == "admin_cliente":
                    new_user_role = "admin_cliente"
            except ValueError as ex:
                logger.info(f"[ONBOARD] invite_invalid reason={ex}")
                return Response({"detail": "invite_invalid"}, status=400)

        # Idempotencia: si ya existe, devolver tokens (si querés promoción para existentes, se puede agregar)
        user = User.objects.filter(email=email).first()
        if user:
            if getattr(user, "tipo_usuario", "") != "super_admin" and user.cliente_id != cliente_id:
                logger.info("[ONBOARD] user_tenant_mismatch email_mask=%s***", email[:2])
                return Response({"detail": "tenant_mismatch"}, status=403)
            return Response(_issue_tokens_for_user(user, "/"), status=200)

        # Crear usuario (respeta rol del invite)
        try:
            user = User.objects.create_user(
                username=email,
                email=email,
                password=None,  # unusable
                tipo_usuario=new_user_role,
                cliente_id=cliente_id,
                oauth_provider="google",
                oauth_uid=sub,
                nombre=nombre,
                apellido=apellido,
                telefono=(body.get("telefono") or "").strip(),
            )
            if hasattr(user, "set_unusable_password"):
                user.set_unusable_password()
                user.save(update_fields=["password"])

            logger.info(f"[ONBOARD] ok user_id={user.id} cliente_id={cliente_id} role={new_user_role}")
            return Response(_issue_tokens_for_user(user, "/"), status=201)

        except Exception:
            logger.error(f"[ONBOARD] unexpected_error email_mask={str(email)[:2]}***", exc_info=True)
            return Response({"detail": "unexpected_error"}, status=500)


class IssueInviteView(APIView):
    permission_classes = [IsAuthenticated & (EsSuperAdmin | EsAdminDeSuCliente)]

    def post(self, request):
        body = request.data or {}
        role = (body.get("role") or "usuario_final").strip()
        if role not in ("usuario_final", "admin_cliente"):
            return Response({"detail": "invalid_role"}, status=400)

        ttl_seconds = int(body.get("ttl_seconds") or 7 * 24 * 3600)
        email = (body.get("email") or "").strip() or None

        req_user = request.user
        if req_user.tipo_usuario == "super_admin":
            cliente_id = body.get("cliente_id")
            if not cliente_id:
                return Response({"detail": "cliente_id_required_for_superadmin"}, status=400)
        else:
            if not getattr(req_user, "cliente_id", None):
                return Response({"detail": "admin_without_cliente"}, status=403)
            cliente_id = body.get("cliente_id") or req_user.cliente_id
            if int(cliente_id) != int(req_user.cliente_id):
                return Response({"detail": "forbidden_other_cliente"}, status=403)

        payload = {
            "v": 1,
            "intent": "invite",
            "cliente_id": int(cliente_id),
            "role": role,
            "email": email,         # opcional
            "issued_by": req_user.id,
        }
        token = sign_state(payload, settings.SECRET_KEY, ttl_seconds=ttl_seconds)
        logger.info(f"[INVITE ISSUE] by={req_user.id} cliente_id={cliente_id} role={role} email={'y' if email else 'n'}")
        return Response({"invite": token}, status=201)
