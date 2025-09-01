// src/components/layout/Navbar.jsx
import React, { useEffect, useContext } from 'react';
import {
  Box, Flex, Text, IconButton, Tooltip, useColorMode, useToast,
} from '@chakra-ui/react';
import { MoonIcon, SunIcon, SmallCloseIcon } from '@chakra-ui/icons'; // 👈 uso SmallClose como icono de salir
import { AuthContext, useAuth } from '../../auth/AuthContext';
import { useNavbarTokens } from '../theme/tokens';
import Button from '../ui/Button';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import NotificationBellInline from '../notifications/NotificationBellInline';
import { useUnreadCount } from '../../hooks/useUnreadCount';

const Navbar = () => {
  const { colorMode, toggleColorMode } = useColorMode();
  const { user, logout } = useAuth();
  const { accessToken } = useContext(AuthContext);
  const navigate = useNavigate();
  const toast = useToast();

  const { bg, borderColor, color, iconColor, hoverColor, textColor, emailOpacity } = useNavbarTokens();
  const { count: unread } = useUnreadCount(accessToken, { pollMs: 60000 });

  const isAdmin = user?.tipo_usuario === 'super_admin' || user?.tipo_usuario === 'admin_cliente';
  const titulo = isAdmin ? 'AdminPadel' : 'Padel App';

  const goToNotifications = () => {
    navigate(isAdmin ? '/admin/notificaciones' : '/notificaciones');
  };

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
      px={{ base: 3, md: 8 }}           // 👈 más compacto en mobile
      py={{ base: 2, md: 4 }}           // 👈 más compacto en mobile
      boxShadow="lg"
      borderBottom={`2px solid ${borderColor}`}
    >
      <Flex
        justify="space-between"
        align="center"
        flexWrap={{ base: 'nowrap', md: 'nowrap' }}   // 👈 una sola línea en mobile
        rowGap={{ base: 0, md: 0 }}
        columnGap={{ base: 2, md: 0 }}
        minW={0}
      >
        {/* Izquierda: título */}
        <Text
          fontWeight="bold"
          fontSize={{ base: 'lg', md: 'xl' }}
          letterSpacing="wide"
          color={textColor}
          minW={0}
          flex={{ base: '1 1 auto', md: '0 0 auto' }} // 👈 permite elipsis en mobile
          noOfLines={1}
        >
          {titulo}
        </Text>

        {/* Derecha: acciones */}
        <Flex
          align="center"
          gap={{ base: 1.5, md: 4 }}       // 👈 menos gap en mobile
          justify="flex-end"
          minW={0}
          flexShrink={0}
        >
          {/* Email oculto en mobile, visible en md+ */}
          <Text
            display={{ base: 'none', md: 'block' }}
            fontSize="sm"
            color={textColor}
            opacity={emailOpacity}
            noOfLines={1}
            maxW="28ch"
            title={user?.email}
          >
            {user?.email}
          </Text>

          <NotificationBellInline count={unread} onClick={goToNotifications} />

          {/* Botón Turnos: sólo desktop/tablet */}
          {user?.tipo_usuario === 'empleado_cliente' && (
            <Button
              size="sm"
              variant="secondary"
              as={RouterLink}
              to="/profesores/turnos"
              display={{ base: 'none', md: 'inline-flex' }}   // 👈 oculto en mobile
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

          {/* Logout: icono en mobile, botón en md+ */}
          <Tooltip label="Cerrar sesión" hasArrow display={{ base: 'block', md: 'none' }}>
            <IconButton
              aria-label="Cerrar sesión"
              icon={<SmallCloseIcon />}       // 👈 icono compacto
              onClick={logout}
              variant="solid"
              size="sm"
              display={{ base: 'inline-flex', md: 'none' }}
            />
          </Tooltip>

          <Button
            size="sm"
            variant="solid"
            onClick={logout}
            whiteSpace="nowrap"
            flexShrink={0}
            display={{ base: 'none', md: 'inline-flex' }}     // 👈 botón completo sólo en md+
          >
            Cerrar sesión
          </Button>
        </Flex>
      </Flex>
    </Box>
  );
};

export default Navbar;
