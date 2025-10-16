// src/components/notifications/NotificationBellInline.jsx
import React from "react";
import {
  Box,
  IconButton,
  Tooltip,
  Text,
  VisuallyHidden,
  useBreakpointValue,
} from "@chakra-ui/react";
import { BellIcon } from "@chakra-ui/icons";

const NotificationBellInline = ({
  count = 0,
  onClick = () => {},
  "aria-label": ariaLabel,
  showTooltip = true, // permite desactivar tooltip si molestara en mobile
}) => {
  const btnSize = useBreakpointValue({ base: "sm", md: "sm" }); // compacto pero touch-friendly
  const label =
    ariaLabel ||
    (count > 0 ? `Tenés ${count} notificación${count > 1 ? "es" : ""} sin leer` : "Notificaciones");

  const ButtonEl = (
    <IconButton
      aria-label={label}
      icon={<BellIcon />}
      onClick={onClick}
      variant="ghost"
      size={btnSize}
      isRound
      // Evita que colapse en contenedores con poco espacio
      flexShrink={0}
    />
  );

  return (
    <Box position="relative" display="inline-block" minW={0}>
      {showTooltip ? (
        <Tooltip label={label} hasArrow openDelay={200}>
          {ButtonEl}
        </Tooltip>
      ) : (
        ButtonEl
      )}

      {count > 0 && (
        <Box
          as="span"
          position="absolute"
          top={{ base: "0", md: "0" }}
          right={{ base: "0", md: "0" }}
          minW={{ base: "18px", md: "18px" }}
          h={{ base: "18px", md: "18px" }}
          px={{ base: "1", md: "1" }}
          bg="red.500"
          color="white"
          borderRadius="full"
          fontSize={{ base: "xs", md: "xs" }}
          display="flex"
          alignItems="center"
          justifyContent="center"
          lineHeight="1"
          pointerEvents="none"
          boxShadow="0 0 0 1px rgba(0,0,0,0.2)"
        >
          <VisuallyHidden>{`${count} sin leer`}</VisuallyHidden>
          <Text as="span">{count > 99 ? "99+" : count}</Text>
        </Box>
      )}
    </Box>
  );
};

export default NotificationBellInline;
