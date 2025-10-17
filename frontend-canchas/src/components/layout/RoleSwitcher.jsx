// src/components/layout/RoleSwitcher.jsx
/**
 * Componente para cambiar roles en tiempo real.
 * Solo se muestra si el usuario tiene múltiples roles disponibles.
 * Permite cambio dinámico de rol con re-login automático.
 */
import React, { useState } from 'react';
import {
  Box,
  Button,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  Text,
  useColorModeValue,
  useBreakpointValue,
  Icon,
  HStack,
  Spinner,
} from '@chakra-ui/react';
import { ChevronDownIcon, StarIcon } from '@chakra-ui/icons';
import { useRoleSwitcher } from '../../hooks/useRoleSwitcher';

const ROLE_LABELS = {
  super_admin: 'Super Admin',
  admin_cliente: 'Admin',
  manager: 'Manager',
  coach: 'Coach',
  receptionist: 'Recepcionista',
  empleado_cliente: 'Empleado',
  usuario_final: 'Usuario',
};

const ROLE_COLORS = {
  super_admin: 'purple',
  admin_cliente: 'blue',
  manager: 'green',
  coach: 'orange',
  receptionist: 'teal',
  empleado_cliente: 'cyan',
  usuario_final: 'gray',
};

const ROLE_ICONS = {
  super_admin: '👑',
  admin_cliente: '⚙️',
  manager: '📊',
  coach: '🏆',
  receptionist: '🏢',
  empleado_cliente: '👨‍💼',
  usuario_final: '👤',
};

const RoleSwitcher = () => {
  const { selectedRole, availableRoles, hasMultipleRoles, changeRole } = useRoleSwitcher();
  const [isChanging, setIsChanging] = useState(false);
  
  console.log('🎭 [RoleSwitcher] Renderizando. hasMultipleRoles:', hasMultipleRoles, 'availableRoles:', availableRoles);
  
  const isMobile = useBreakpointValue({ base: true, md: false });
  
  // Definir todos los colores al inicio para evitar problemas con hooks
  const menuListBg = useColorModeValue('white', 'gray.800');
  const menuListBorderColor = useColorModeValue('gray.200', 'gray.600');
  const headerBorderColor = useColorModeValue('gray.200', 'gray.600');
  const headerTextColor = useColorModeValue('gray.600', 'gray.400');
  const itemTextColor = useColorModeValue('gray.700', 'gray.200');
  const selectedBg = useColorModeValue('blue.50', 'blue.900');
  const selectedHoverBg = useColorModeValue('blue.100', 'blue.800');
  const hoverBg = useColorModeValue('gray.50', 'gray.700');
  const footerBorderColor = useColorModeValue('gray.200', 'gray.600');
  const footerTextColor = useColorModeValue('gray.500', 'gray.400');

  // Solo mostrar si tiene múltiples roles
  if (!hasMultipleRoles) {
    return null;
  }

  const currentRoleLabel = ROLE_LABELS[selectedRole] || selectedRole;
  const currentRoleIcon = ROLE_ICONS[selectedRole] || '👤';
  
  console.log('🎭 [RoleSwitcher] selectedRole:', selectedRole);
  console.log('🎭 [RoleSwitcher] currentRoleLabel:', currentRoleLabel);
  console.log('🎭 [RoleSwitcher] currentRoleIcon:', currentRoleIcon);

  return (
    <Menu>
      <MenuButton
        as={Button}
        variant="ghost"
        size={isMobile ? "xs" : "sm"}
        rightIcon={<ChevronDownIcon boxSize={isMobile ? 3 : 4} />}
        bg="rgba(255, 255, 255, 0.1)"
        color="white"
        _active={{ bg: 'rgba(255, 255, 255, 0.2)', color: 'white' }}
        minW={isMobile ? '100px' : '120px'}
        maxW={isMobile ? '140px' : '160px'}
        px={isMobile ? 3 : 4}
        py={isMobile ? 1.5 : 2}
        borderRadius="md"
        border="1px solid"
        borderColor="rgba(255, 255, 255, 0.2)"
        _hover={{ 
          bg: 'rgba(255, 255, 255, 0.2)', 
          color: 'white',
          borderColor: 'rgba(255, 255, 255, 0.3)' 
        }}
        h={isMobile ? '32px' : '36px'}
      >
        <HStack spacing={isMobile ? 1.5 : 2.5} minW={0} overflow="hidden">
          {isChanging ? (
            <Spinner size={isMobile ? "xs" : "sm"} color="white" />
          ) : (
            <Text fontSize="xs" color="white" flexShrink={0}>{currentRoleIcon}</Text>
          )}
          <Text 
            fontSize={isMobile ? "xs" : "sm"} 
            fontWeight="medium" 
            noOfLines={1} 
            color="white"
            display={isMobile ? "none" : "block"}
            overflow="hidden"
            textOverflow="ellipsis"
            whiteSpace="nowrap"
            flex={1}
            minW={0}
          >
            {isChanging ? 'Cambiando...' : currentRoleLabel}
          </Text>
        </HStack>
      </MenuButton>
      
              <MenuList
                bg={menuListBg}
                minW={isMobile ? "180px" : "200px"}
                maxW={isMobile ? "240px" : "260px"}
                w={isMobile ? "90vw" : "auto"}
                borderRadius="lg"
                boxShadow="xl"
                border="1px solid"
                borderColor={menuListBorderColor}
                maxH={isMobile ? "60vh" : "auto"}
                overflowY="auto"
                overflowX="hidden"
                wordWrap="break-word"
                whiteSpace="nowrap"
              >
        <Box px={isMobile ? 2 : 3} py={isMobile ? 1.5 : 2} borderBottom="1px solid" borderColor={headerBorderColor}>
          <Text fontSize={isMobile ? "2xs" : "xs"} color={headerTextColor} fontWeight="medium">
            Cambiar vista
          </Text>
        </Box>
        
        {availableRoles.map((role) => {
          const isSelected = role === selectedRole;
          const roleLabel = ROLE_LABELS[role] || role;
          const roleIcon = ROLE_ICONS[role] || '👤';
          
          return (
            <MenuItem
              key={role}
              onClick={async () => {
                setIsChanging(true);
                await changeRole(role);
                setIsChanging(false);
              }}
              bg={isSelected ? selectedBg : 'transparent'}
              _hover={{ bg: isSelected ? selectedHoverBg : hoverBg }}
              py={isMobile ? 1.5 : 2}
              px={isMobile ? 2 : 3}
              borderRadius="md"
              mx={isMobile ? 1 : 1.5}
              my={isMobile ? 0.25 : 0.5}
              isDisabled={isChanging}
              w="100%"
              maxW="100%"
              overflow="hidden"
            >
              <HStack spacing={isMobile ? 1.5 : 2} w="100%" minW={0} justify="space-between" overflow="hidden">
                <HStack spacing={isMobile ? 1.5 : 2} minW={0} flex={1} overflow="hidden">
                  <Text fontSize={isMobile ? "xs" : "sm"} flexShrink={0}>{roleIcon}</Text>
                  <Text 
                    fontSize={isMobile ? "2xs" : "xs"} 
                    fontWeight={isSelected ? "semibold" : "medium"}
                    noOfLines={1}
                    title={roleLabel}
                    color={itemTextColor}
                    overflow="hidden"
                    textOverflow="ellipsis"
                    whiteSpace="nowrap"
                    flex={1}
                    minW={0}
                  >
                    {roleLabel}
                  </Text>
                </HStack>
                {isSelected && (
                  <Icon 
                    as={StarIcon} 
                    color="blue.500" 
                    boxSize={isMobile ? 2.5 : 3} 
                    flexShrink={0}
                    ml={isMobile ? 0.5 : 1}
                  />
                )}
              </HStack>
            </MenuItem>
          );
        })}
        
        <Box px={isMobile ? 2 : 3} py={isMobile ? 1 : 1.5} borderTop="1px solid" borderColor={footerBorderColor}>
          <Text fontSize={isMobile ? "2xs" : "xs"} color={footerTextColor} textAlign="center">
            {availableRoles.length} rol{availableRoles.length > 1 ? 'es' : ''} disponible{availableRoles.length > 1 ? 's' : ''}
          </Text>
        </Box>
      </MenuList>
    </Menu>
  );
};

export default RoleSwitcher;
