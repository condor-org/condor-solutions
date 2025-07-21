import React from 'react';
import {
  Box,
  Flex,
  Text,
  IconButton,
  Tooltip,
  useColorMode,
} from '@chakra-ui/react';
import { MoonIcon, SunIcon } from '@chakra-ui/icons';
import { useAuth } from '../../auth/AuthContext';
import { useNavbarTokens } from '../theme/tokens';
import Button from '../ui/Button';

const Navbar = () => {
  const { colorMode, toggleColorMode } = useColorMode();
  const { user, logout } = useAuth();
  const {
    bg,
    borderColor,
    color,
    iconColor,
    hoverColor,
    textColor,
    emailOpacity,
    mode
  } = useNavbarTokens();

  const titulo = user?.tipo === 'admin' ? 'AdminPadel' : 'Padel App';

  // 🔍 Debug logs
  console.log("🔄 Navbar render");
  console.log("🧭 colorMode desde Chakra:", colorMode);
  console.log("🎨 mode desde tokens:", mode);
  console.log("🖌️ bg actual:", bg);
  console.log("🌈 textColor:", textColor);
  console.log("🎯 iconColor:", iconColor);
  console.log("🌗 toggle funciona:", colorMode === 'light' ? 'Switching to dark' : 'Switching to light');

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
