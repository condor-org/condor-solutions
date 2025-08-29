// src/components/layout/Navbar.jsx
import React, { useEffect, useContext } from 'react';
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
import { AuthContext, useAuth } from '../../auth/AuthContext';
import { useNavbarTokens } from '../theme/tokens';
import Button from '../ui/Button';
import { Link as RouterLink, useNavigate } from 'react-router-dom';

import NotificationBellInline from '../notifications/NotificationBellInline';
import { useUnreadCount } from '../../hooks/useUnreadCount';

const Navbar = () => {
  const { colorMode, toggleColorMode } = useColorMode();
  const { user, logout } = useAuth();
  const { accessToken } = useContext(AuthContext); // ✅ para el contador
  const navigate = useNavigate();
  const toast = useToast();

  const {
    bg, borderColor, color, iconColor, hoverColor, textColor, emailOpacity,
  } = useNavbarTokens();

  // 🔔 contador de no leídas (usa token)
  const { count: unread } = useUnreadCount(accessToken, { pollMs: 60000 });

  const isAdmin = user?.tipo_usuario === 'super_admin' || user?.tipo_usuario === 'admin_cliente';
  const titulo = isAdmin ? 'AdminPadel' : 'Padel App';

  // 🧭 ir a la vista correcta según rol
  const goToNotifications = () => {
    navigate(isAdmin ? '/admin/notificaciones' : '/notificaciones');
  };

  // 🍞 Toast “Tenés X sin leer” una vez por sesión
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

  return (
    <Box
      as="nav"
      position="sticky"
      top="0"
      zIndex="100"
      width="100%"
      bg={bg}
      color={color}
      px={{ base: 4, md: 8 }}
      py={{ base: 3, md: 4 }}
      boxShadow="lg"
      borderBottom={`2px solid ${borderColor}`}
    >
      <Flex
        justify="space-between"
        align="center"
        // ✅ En móvil permitimos que el bloque derecho salte de línea
        flexWrap={{ base: 'wrap', md: 'nowrap' }}
        rowGap={{ base: 3, md: 0 }}
      >
        {/* Izquierda: título */}
        <Text
          fontWeight="bold"
          fontSize={{ base: 'lg', md: 'xl' }}
          letterSpacing="wide"
          color={textColor}
          // Evita que el título empuje si es largo
          minW={0}
        >
          {titulo}
        </Text>

        {/* Derecha: acciones */}
        <Flex
          align="center"
          gap={{ base: 2, md: 4 }}
          // En móvil, que ocupe toda la fila si baja
          w={{ base: '100%', md: 'auto' }}
          justify={{ base: 'flex-end', md: 'flex-end' }}
          minW={0}
        >
          <Text
            fontSize="sm"
            color={textColor}
            opacity={emailOpacity}
            // ✅ Truncar email largo en móvil
            noOfLines={1}
            maxW={{ base: '40%', sm: '50%', md: 'unset' }}
            title={user?.email}
          >
            {user?.email}
          </Text>

          {/* 🔔 Campanita con contador y navegación por rol */}
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
              flexShrink={0}
            />
          </Tooltip>

          <Button
            size="sm"
            variant="solid"
            onClick={logout}
            // Evita que el botón colapse texto en pantallas muy chicas
            whiteSpace="nowrap"
            flexShrink={0}
          >
            Cerrar sesión
          </Button>
        </Flex>
      </Flex>
    </Box>
  );
};

export default Navbar;
