// src/components/notifications/NotificationBell.jsx
import React, { useContext } from "react";
import { IconButton, Box, useBreakpointValue, VisuallyHidden } from "@chakra-ui/react";
import { FaBell } from "react-icons/fa";
import { AuthContext } from "../../auth/AuthContext";
import { useUnreadCount } from "../../hooks/useUnreadCount";
import { useNavbarTokens } from "../theme/tokens";

/**
 * Campanita con badge. Usa tokens de navbar.
 * - onClick: abrir drawer / navegar a /notificaciones (lo decidís vos)
 * - pollMs: override opcional del polling
 */
const NotificationBell = ({ onClick, pollMs = 60000, "aria-label": ariaLabel }) => {
  const { accessToken } = useContext(AuthContext);
  const { count, loading } = useUnreadCount(accessToken, { pollMs });
  const tokens = useNavbarTokens();

  // Tamaño del botón responsivo para mobile/desktop
  const btnSize = useBreakpointValue({ base: "sm", md: "md" });

  // A11y label dinámico
  const label =
    ariaLabel || (count > 0 ? `Tenés ${count} notificación${count > 1 ? "es" : ""} sin leer` : "Notificaciones");

  return (
    <Box position="relative" display="inline-block" minW={0}>
      <IconButton
        aria-label={label}
        icon={<FaBell />}
        onClick={onClick}
        variant="ghost"
        size={btnSize}
        color={tokens.iconColor}
        _hover={{ bg: tokens.hoverColor ? `${tokens.hoverColor}33` : "whiteAlpha.200" }}
        // Evita que el botón se achique y empuje otros elementos en contenedores flex
        flexShrink={0}
      />
      {!loading && count > 0 && (
        <Box
          position="absolute"
          // Ubicación estable para ambas densidades
          top={{ base: "-2px", md: "-3px" }}
          right={{ base: "-2px", md: "-3px" }}
          bg="red.500"
          color="white"
          minW={{ base: "18px", md: "20px" }}
          h={{ base: "18px", md: "20px" }}
          px={{ base: "1.5", md: "1.5" }}
          rounded="full"
          fontSize={{ base: "11px", md: "12px" }}
          fontWeight="bold"
          lineHeight={{ base: "18px", md: "20px" }}
          textAlign="center"
          pointerEvents="none"
          // Sombra sutil para contraste en temas claros/oscuros
          boxShadow="0 0 0 1px rgba(0,0,0,0.2)"
        >
          <VisuallyHidden>{`${count} sin leer`}</VisuallyHidden>
          {count > 99 ? "99+" : count}
        </Box>
      )}
    </Box>
  );
};

export default NotificationBell;
