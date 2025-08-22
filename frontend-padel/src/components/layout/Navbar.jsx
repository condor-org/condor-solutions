import React, { useEffect } from 'react';
import {
  Box,
  Flex,
  Text,
  IconButton,
  Tooltip,
  useColorMode,
  useToast,
} from '@chakra-ui/react';
import { MoonIcon, SunIcon } from '@chakra-ui/icons';
import { useAuth } from '../../auth/AuthContext';
import { useNavbarTokens } from '../theme/tokens';
import Button from '../ui/Button';
import { Link as RouterLink, useNavigate } from 'react-router-dom';

import NotificationBellInline from '../notifications/NotificationBellInline';
import { useUnreadCount } from '../../hooks/useUnreadCount';

const Navbar = () => {
  const { colorMode, toggleColorMode } = useColorMode();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();

  const {
    bg, borderColor, color, iconColor, hoverColor, textColor, emailOpacity,
  } = useNavbarTokens();

  // 🔔 contador de no leídas (polling liviano + refresh por event bus si lo tenés)
  const { count: unread } = useUnreadCount(
    // accessToken lo toma internamente desde axiosAuth si así lo definiste;
    // si tu hook requiere el token explícito, pásalo desde el AuthContext
    // p.ej: useUnreadCount(accessToken, { pollMs: 60000 })
    undefined,
    { pollMs: 60000 }
  );

  const titulo = (user?.tipo_usuario === 'super_admin' || user?.tipo_usuario === 'admin_cliente')
    ? 'AdminPadel'
    : 'Padel App';



  // 🍞 Mostrar toast “Tenés X sin leer” solo una vez por sesión (por usuario)
  useEffect(() => {
    if (!user?.id) return;
    const key = `notif_toast_shown:${user.id}`;
    if (unread > 0 && !sessionStorage.getItem(key)) {
      toast({
        title: `¡Tenés ${unread} notificación(es) sin leer!`,
        status: 'info',
        duration: 4000,
        isClosable: true,
        position: 'top-right',
        variant: 'subtle',
      });
      sessionStorage.setItem(key, String(Date.now()));
    }
  }, [unread, user?.id, toast]);

  const goToNotifications = () => navigate('/notificaciones');

  return (
    <Box
      as="nav"
      position="sticky"
      top="0"
      zIndex="100"
      width="100%"
      bg={bg}
      color={color}
      px={8}
      py={4}
      boxShadow="lg"
      borderBottom={`2px solid ${borderColor}`}
    >
      <Flex justify="space-between" align="center">
        <Text fontWeight="bold" fontSize="xl" letterSpacing="wide" color={textColor}>
          {titulo}
        </Text>

        <Flex align="center" gap={4}>
          <Text fontSize="sm" color={textColor} opacity={emailOpacity}>
            {user?.email}
          </Text>

          {/* 🔔 Campanita con contador y navegación */}
          <NotificationBellInline count={unread} onClick={goToNotifications} />

          {user?.tipo_usuario === "empleado_cliente" && (
            <Button
              size="sm"
              variant="secondary"
              as={RouterLink}
              to="/profesores/turnos"
            >
              Turnos
            </Button>
          )}

          <Tooltip label="Cambiar modo" hasArrow>
            <IconButton
              aria-label="Toggle modo claro/oscuro"
              icon={colorMode === 'light' ? <MoonIcon /> : <SunIcon />}
              onClick={toggleColorMode}
              variant="ghost"
              size="sm"
              isRound
              color={iconColor}
              _hover={{ color: hoverColor }}
            />
          </Tooltip>

          <Button size="sm" variant="solid" onClick={logout}>
            Cerrar sesión
          </Button>
        </Flex>
      </Flex>
    </Box>
  );
};

export default Navbar;
