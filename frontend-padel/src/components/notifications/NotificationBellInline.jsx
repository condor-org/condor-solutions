// src/components/notifications/NotificationBellInline.jsx
import React from 'react';
import { Box, IconButton, Tooltip, Text, VisuallyHidden } from '@chakra-ui/react';
import { BellIcon } from '@chakra-ui/icons';

const NotificationBellInline = ({
  count = 0,
  onClick = () => {},
  'aria-label': ariaLabel,
}) => {
  const label =
    ariaLabel ||
    (count > 0 ? `Tenés ${count} notificación(es) sin leer` : 'Notificaciones');

  return (
    <Box position="relative" display="inline-block">
      <Tooltip label={label} hasArrow>
        <IconButton
          aria-label={label}
          icon={<BellIcon />}
          onClick={onClick}
          variant="ghost"
          size="sm"
          isRound
        />
      </Tooltip>

      {count > 0 && (
        <Box
          as="span"
          position="absolute"
          top="0"
          right="0"
          minW="18px"
          h="18px"
          px="1"
          bg="red.500"
          color="white"
          borderRadius="full"
          fontSize="xs"
          display="flex"
          alignItems="center"
          justifyContent="center"
          lineHeight="1"
          pointerEvents="none"
        >
          <VisuallyHidden>{`${count} sin leer`}</VisuallyHidden>
          <Text as="span">{count > 99 ? '99+' : count}</Text>
        </Box>
      )}
    </Box>
  );
};

export default NotificationBellInline;
