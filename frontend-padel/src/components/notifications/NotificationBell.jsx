import React, { useContext } from "react";
import { IconButton, Box } from "@chakra-ui/react";
import { FaBell } from "react-icons/fa";
import { AuthContext } from "../../auth/AuthContext";
import { useUnreadCount } from "../../hooks/useUnreadCount";
import { useNavbarTokens } from "../theme/tokens";

/**
 * Campanita con badge. Usa tokens de navbar.
 * - onClick: abrir drawer / navegar a /notificaciones (lo decidís vos)
 * - pollMs: override opcional del polling
 */
const NotificationBell = ({ onClick, pollMs = 60000 }) => {
  const { accessToken } = useContext(AuthContext);
  const { count, loading } = useUnreadCount(accessToken, { pollMs });
  const tokens = useNavbarTokens();

  return (
    <Box position="relative" display="inline-block">
      <IconButton
        aria-label="Notificaciones"
        icon={<FaBell />}
        onClick={onClick}
        variant="ghost"
        size="md"
        color={tokens.iconColor}
        _hover={{ bg: tokens.hoverColor ? `${tokens.hoverColor}33` : "whiteAlpha.200" }}
      />
      {!loading && count > 0 && (
        <Box
          position="absolute"
          top="-2px"
          right="-2px"
          bg="red.500"
          color="white"
          minW="18px"
          h="18px"
          px="1.5"
          rounded="full"
          fontSize="11px"
          fontWeight="bold"
          lineHeight="18px"
          textAlign="center"
        >
          {count > 99 ? "99+" : count}
        </Box>
      )}
    </Box>
  );
};

export default NotificationBell;
