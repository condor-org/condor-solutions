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

from .serializers import UsuarioSerializer
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

def _issue_tokens_for_user(user, return_to="/", cliente_actual=None):
    # ✅ LOG: Cliente que se usa para el JWT
    logger.info(f"[ISSUE TOKENS] cliente_actual={cliente_actual.nombre if cliente_actual else 'None'} user_id={user.id}")
    
    refresh = RefreshToken.for_user(user)
    access = refresh.access_token
    access["email"] = user.email
    access["is_super_admin"] = user.is_super_admin
    
    # Configurar rol y roles para el nuevo sistema multi-tenant
    if cliente_actual:
        access["cliente_id"] = cliente_actual.id  # ✅ Usar cliente_actual
        # ✅ LOG: JWT cliente_id
        logger.info(f"[ISSUE TOKENS] jwt_cliente_id={cliente_actual.id}")
        
        roles_en_cliente = user.get_roles_en_cliente(cliente_actual.id)
        # Usar el primer rol disponible como rol activo (el usuario puede cambiarlo después)
        rol_en_cliente = roles_en_cliente[0] if roles_en_cliente else "usuario_final"
        access["rol_en_cliente"] = rol_en_cliente
        access["roles_en_cliente"] = roles_en_cliente
    else:
        # Fallback al sistema antiguo
        access["cliente_id"] = user.cliente_id
        access["tipo_usuario"] = user.tipo_usuario
        access["rol_en_cliente"] = user.tipo_usuario
        access["roles_en_cliente"] = [user.tipo_usuario]
    
    return {
        "ok": True,
        "access": str(access),
        "refresh": str(refresh),
        "user": {
            "id": user.id,
            "email": user.email,
            "nombre": getattr(user, "nombre", None),
            "apellido": getattr(user, "apellido", None),
            "telefono": getattr(user, "telefono", None),
            "tipo_usuario": user.tipo_usuario,  # Mantener para compatibilidad
            "cliente_id": user.cliente_id,
        },
        "return_to": return_to,
    }
# ==========================
# Vistas existentes
# ==========================

class MiPerfilView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        cliente_actual = getattr(request, 'cliente_actual', None)
        
        # ✅ LOG: Cliente que se devuelve al frontend
        logger.info(f"[MI PERFIL] cliente_actual={cliente_actual.nombre if cliente_actual else 'None'} user_id={user.id}")
        
        # Importar y usar la función helper
        from .utils import get_rol_actual_del_jwt
        rol_actual = get_rol_actual_del_jwt(request)
        
        # Información del cliente actual
        cliente_actual_info = None
        if cliente_actual:
            # Usar el rol del JWT si está disponible, sino el primer rol disponible
            roles_en_cliente = user.get_roles_en_cliente(cliente_actual.id)
            rol_en_cliente = rol_actual or (roles_en_cliente[0] if roles_en_cliente else "usuario_final")
            
            cliente_actual_info = {
                "id": cliente_actual.id,
                "nombre": cliente_actual.nombre,
                "rol": rol_en_cliente,
                "roles": roles_en_cliente,
                "tipo_cliente": cliente_actual.tipo_cliente,
                "tipo_fe": getattr(cliente_actual, 'tipo_fe', cliente_actual.tipo_cliente),
            }
        
        # En un sistema multi-tenant por hostname, solo mostramos el cliente actual
        # No exponemos otros clientes por seguridad
        clientes_usuario = []
        if cliente_actual:
            # Solo mostrar el cliente actual con sus roles
            roles_en_cliente = user.get_roles_en_cliente(cliente_actual.id)
            for rol in roles_en_cliente:
                clientes_usuario.append({
                    "id": cliente_actual.id,
                    "nombre": cliente_actual.nombre,
                    "rol": rol,
                    "tipo_cliente": cliente_actual.tipo_cliente,
                    "tipo_fe": getattr(cliente_actual, 'tipo_fe', cliente_actual.tipo_cliente),
                })
        
        data = {
            "id": user.id,
            "email": user.email,
            "nombre": getattr(user, "nombre", None),
            "apellido": getattr(user, "apellido", None),
            "telefono": getattr(user, "telefono", None),
            "is_super_admin": user.is_super_admin,
            "cliente_actual": cliente_actual_info,
            "clientes": clientes_usuario,
            # Backward compatibility
            "tipo_usuario": getattr(user, "tipo_usuario", None),
            "cliente_id": getattr(user, "cliente_id", None),
        }
        logger.debug(f"[YO VIEW] user_id={user.id} cliente_actual={cliente_actual_info} clientes={len(clientes_usuario)}")
        return Response(data)

class UsuarioViewSet(viewsets.ModelViewSet):
    serializer_class = UsuarioSerializer
    permission_classes = [IsAuthenticated & (EsSuperAdmin | EsAdminDeSuCliente)]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['id', 'email', 'tipo_usuario']

    def get_queryset(self):
        user = self.request.user
        cliente_actual = getattr(self.request, 'cliente_actual', None)
        
        # Importar y usar la función helper
        from .utils import get_rol_actual_del_jwt
        rol_actual = get_rol_actual_del_jwt(self.request)
        
        # Super admin: si accede desde un dominio específico, filtrar por ese cliente
        if user.is_super_admin:
            if cliente_actual:
                # Super admin accediendo desde un cliente específico: filtrar por ese cliente
                from apps.auth_core.models import UserClient
                usuarios_ids = UserClient.objects.filter(
                    cliente=cliente_actual,
                    activo=True
                ).values_list('usuario_id', flat=True)
                return Usuario.objects.filter(id__in=usuarios_ids)
            else:
                # Super admin accediendo sin cliente específico: mostrar todos
                return Usuario.objects.all()
        # Admin del cliente → SOLO usuarios que tienen roles en SU cliente
        elif rol_actual == "admin_cliente" and cliente_actual:
            from apps.auth_core.models import UserClient
            # Obtener usuarios que tienen UserClient activo en el cliente actual
            usuarios_ids = UserClient.objects.filter(
                cliente=cliente_actual,
                activo=True
            ).values_list('usuario_id', flat=True)
            return Usuario.objects.filter(id__in=usuarios_ids)
        else:
            return Usuario.objects.none()

    def list(self, request, *args, **kwargs):
        """
        Lista usuarios mostrando una entrada por cada rol que tengan.
        """
        from apps.auth_core.models import UserClient
        
        # Obtener usuarios base
        usuarios = self.get_queryset()
        
        # Crear lista de usuarios con roles
        usuarios_con_roles = []
        
        for usuario in usuarios:
            # Obtener todos los roles del usuario en el cliente actual
            cliente_actual = getattr(request, 'cliente_actual', None)
            
            if usuario.is_super_admin:
                # Super admin aparece una vez con rol super_admin
                usuarios_con_roles.append({
                    'usuario': usuario,
                    'rol': 'super_admin',
                    'cliente': None
                })
            else:
                # Obtener el rol actual del usuario
                from .utils import get_rol_actual_del_jwt
                rol_actual = get_rol_actual_del_jwt(request)
                cliente_actual = getattr(request, 'cliente_actual', None)
                
                if rol_actual == "admin_cliente" and cliente_actual:
                    # Admin de cliente: solo mostrar roles del cliente actual
                    user_clients = UserClient.objects.filter(
                        usuario=usuario, 
                        cliente=cliente_actual,
                        activo=True
                    )
                    
                    if user_clients.exists():
                        # Usuario con sistema nuevo: mostrar solo el primer rol del cliente actual
                        user_client = user_clients.first()
                        usuarios_con_roles.append({
                            'usuario': usuario,
                            'rol': user_client.rol,
                            'cliente': user_client.cliente
                        })
                    else:
                        # Usuario con sistema antiguo: mostrar con tipo_usuario solo si es del cliente actual
                        if usuario.cliente == cliente_actual:
                            usuarios_con_roles.append({
                                'usuario': usuario,
                                'rol': usuario.tipo_usuario,
                                'cliente': usuario.cliente
                            })
                else:
                    # Super admin: mostrar todos los roles del usuario
                    user_clients = UserClient.objects.filter(usuario=usuario, activo=True)
                    
                    if user_clients.exists():
                        # Usuario con sistema nuevo: mostrar solo el primer rol
                        user_client = user_clients.first()
                        usuarios_con_roles.append({
                            'usuario': usuario,
                            'rol': user_client.rol,
                            'cliente': user_client.cliente
                        })
                    else:
                        # Usuario con sistema antiguo: mostrar con tipo_usuario
                        usuarios_con_roles.append({
                            'usuario': usuario,
                            'rol': usuario.tipo_usuario,
                            'cliente': usuario.cliente
                        })
        
        # Serializar cada entrada
        serializer = UsuarioSerializer([entry['usuario'] for entry in usuarios_con_roles], many=True)
        data = serializer.data
        
        # Agregar información de rol a cada entrada
        for i, entry in enumerate(usuarios_con_roles):
            data[i]['rol_activo'] = entry['rol']
            # Sobrescribir tipo_usuario con el rol activo para consistencia
            data[i]['tipo_usuario'] = entry['rol']
            if entry['cliente']:
                data[i]['cliente_info'] = {
                    'id': entry['cliente'].id,
                    'nombre': entry['cliente'].nombre
                }
        
        return Response({
            'count': len(data),
            'next': None,
            'previous': None,
            'results': data
        })

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
        redirect_uri = body.get("redirect_uri")
        
        logger.info(f"[OAUTH STATE] request_body={body}")
        logger.info(f"[OAUTH STATE] redirect_uri_from_body={redirect_uri}")

        if not host or not isinstance(host, str):
            return Response({"detail": "host_required"}, status=400)

        # Usar el cliente detectado por el TenantMiddleware
        cliente_actual = getattr(request, 'cliente_actual', None)
        
        # ✅ LOG: Cliente que se va a usar
        logger.info(f"[OAUTH STATE] cliente_actual={cliente_actual.nombre if cliente_actual else 'None'} host={host}")
        
        if not cliente_actual:
            logger.warning(f"[OAUTH STATE] no_cliente_actual host={host}")
            return Response({"detail": "cliente_not_resolved"}, status=400)
        
        cliente_id = cliente_actual.id
        logger.info(f"[OAUTH STATE] using_tenant_cliente host={host} cliente_id={cliente_id} cliente_nombre={cliente_actual.nombre}")

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
        if redirect_uri:
            payload["redirect_uri"] = redirect_uri

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
        redirect_url = f"https://{host}/oauth/google/callback?code={quote(code)}&state={quote(state_raw)}"
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
        
        # ✅ LOG: Cliente del state
        logger.info(f"[OAUTH CB] cliente_id_from_state={cliente_id_state}")
        
        # ✅ LOG: Cliente actual del request
        cliente_actual = getattr(request, 'cliente_actual', None)
        logger.info(f"[OAUTH CB] cliente_actual_from_request={cliente_actual.nombre if cliente_actual else 'None'}")
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
        
        # Usar la URL de redirección del state en lugar de la configurada
        logger.info(f"[OAUTH CB] state_content={state}")
        logger.info(f"[OAUTH CB] state_redirect_uri={state.get('redirect_uri')}")
        logger.info(f"[OAUTH CB] cfg_redirect_uri={cfg.redirect_uri}")
        redirect_uri = state.get("redirect_uri", cfg.redirect_uri)
        logger.info(f"[OAUTH CB] using_redirect_uri={redirect_uri}")
        
        form = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": cfg.client_id,
            "client_secret": cfg.client_secret,
            "redirect_uri": redirect_uri,
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
                # Verificar acceso al cliente usando el nuevo sistema multi-tenant
                if not user.is_super_admin:
                    if cliente_id_state and not user.tiene_acceso_a_cliente(cliente_id_state):
                        logger.info(
                            "[OAUTH CB] user_no_access_to_client user_id=%s cliente_id=%s email_mask=%s***",
                            user.id, cliente_id_state, email[:2]
                        )
                        # Si no tiene acceso, agregar automáticamente como usuario_final
                        from apps.clientes_core.models import Cliente
                        try:
                            cliente = Cliente.objects.get(id=cliente_id_state)
                            user.agregar_rol_a_cliente(cliente, 'usuario_final')
                            logger.info(f"[OAUTH CB] auto_added_user_to_client user_id={user.id} cliente_id={cliente_id_state}")
                        except Cliente.DoesNotExist:
                            logger.warning(f"[OAUTH CB] cliente_not_found cliente_id={cliente_id_state}")
                            return Response({"detail": "cliente_not_found"}, status=400)

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

                cliente_actual = getattr(request, 'cliente_actual', None)
                return Response(_issue_tokens_for_user(user, return_to, cliente_actual), status=200)

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
# Onboarding (siempre requerido para usuarios nuevos)
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
            cliente_actual = getattr(request, 'cliente_actual', None)
            return Response(_issue_tokens_for_user(user, "/", cliente_actual), status=200)

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
            cliente_actual = getattr(request, 'cliente_actual', None)
            return Response(_issue_tokens_for_user(user, "/", cliente_actual), status=201)

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


# ==========================
# Cambio de Rol
# ==========================

class CambiarRolView(APIView):
    """
    Endpoint para cambiar el rol activo del usuario en el cliente actual.
    Emite un nuevo JWT con el rol seleccionado.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        nuevo_rol = request.data.get('rol')
        cliente_actual = getattr(request, 'cliente_actual', None)
        
        if not cliente_actual:
            return Response(
                {"error": "No se pudo determinar el cliente actual"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not nuevo_rol:
            return Response(
                {"error": "Se requiere el campo 'rol'"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verificar que el usuario tenga el rol solicitado en el cliente actual
        if not user.tiene_rol_en_cliente(cliente_actual.id, nuevo_rol):
            return Response(
                {"error": f"El usuario no tiene el rol '{nuevo_rol}' en este cliente"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Emitir nuevos tokens con el rol seleccionado
        try:
            # Usar la función actualizada que acepta cliente_actual
            refresh = RefreshToken.for_user(user)
            access = refresh.access_token
            access["email"] = user.email
            access["is_super_admin"] = user.is_super_admin
            access["cliente_id"] = cliente_actual.id if cliente_actual else None
            access["rol_en_cliente"] = nuevo_rol
            access["roles_en_cliente"] = user.get_roles_en_cliente(cliente_actual.id) if cliente_actual else []
            
            # Obtener información del cliente actual
            cliente_actual_info = None
            if cliente_actual:
                roles_en_cliente = user.get_roles_en_cliente(cliente_actual.id)
                
                cliente_actual_info = {
                    "id": cliente_actual.id,
                    "nombre": cliente_actual.nombre,
                    "rol": nuevo_rol,  # Usar el nuevo rol seleccionado
                    "roles": roles_en_cliente,
                    "tipo_cliente": cliente_actual.tipo_cliente,
                    "tipo_fe": getattr(cliente_actual, 'tipo_fe', cliente_actual.tipo_cliente),
                }
            
            # Obtener todos los clientes del usuario
            clientes_usuario = []
            for user_client in user.get_clientes_activos():
                clientes_usuario.append({
                    "id": user_client.cliente.id,
                    "nombre": user_client.cliente.nombre,
                    "rol": user_client.rol,
                    "tipo_cliente": user_client.cliente.tipo_cliente,
                    "tipo_fe": getattr(user_client.cliente, 'tipo_fe', user_client.cliente.tipo_cliente),
                })
            
            tokens_data = {
                "ok": True,
                "access": str(access),
                "refresh": str(refresh),
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "nombre": getattr(user, "nombre", None),
                    "apellido": getattr(user, "apellido", None),
                    "telefono": getattr(user, "telefono", None),
                    "is_super_admin": user.is_super_admin,
                    "cliente_actual": cliente_actual_info,
                    "clientes": clientes_usuario,
                },
                "return_to": "/",
            }
            
            return Response({
                "ok": True,
                "access": tokens_data["access"],
                "refresh": tokens_data["refresh"],
                "user": tokens_data["user"],
                "message": f"Rol cambiado a {nuevo_rol} exitosamente"
            })
            
        except Exception as e:
            logger.error(f"Error al cambiar rol: {e}")
            return Response(
                {"error": "Error interno al cambiar rol"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
