import React, { useState } from 'react';
import {
  Box,
  Flex,
  Text,
  IconButton,
  Button,
  Stack,
  Collapse,
  Icon,
  Link,
  Popover,
  PopoverTrigger,
  PopoverContent,
  useColorModeValue,
  useBreakpointValue,
  useDisclosure,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  MenuDivider,
  Avatar,
  Badge,
  Divider
} from '@chakra-ui/react';
import {
  HamburgerIcon,
  CloseIcon,
  ChevronDownIcon,
  ChevronRightIcon
} from '@chakra-ui/icons';
import {
  FaUserMd,
  FaHospital,
  FaUser,
  FaCog,
  FaSignOutAlt,
  FaCalendar
} from 'react-icons/fa';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../auth/AuthContext';

const ETHENavbar = () => {
  const { isOpen, onToggle } = useDisclosure();
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();
  
  // Determinar el rol del usuario y las opciones de menú
  const getMenuItems = () => {
    const rol = user?.rol_en_cliente || user?.cliente_actual?.rol || 'paciente';
    
    console.log('🔍 ETHENavbar: User:', user);
    console.log('🔍 ETHENavbar: Rol detectado:', rol);
    console.log('🔍 ETHENavbar: Cliente actual:', user?.cliente_actual);
    
    switch (rol) {
      case 'medico_m1':
        return [
          { label: 'Dashboard', href: '/medico-m1/dashboard', icon: FaUserMd },
          { label: 'Ingresar Paciente', href: '/medico-m1/ingresar-paciente', icon: FaUser },
          { label: 'Mis Pacientes', href: '/medico-m1/pacientes', icon: FaUserMd }
        ];
      
      case 'medico_m2':
        return [
          { label: 'Dashboard', href: '/medico-m2/dashboard', icon: FaUserMd },
          { label: 'Mi Agenda', href: '/medico-m2/agenda', icon: FaCalendar },
          { label: 'Mis Pacientes', href: '/medico-m2/pacientes', icon: FaUser }
        ];
      
      case 'medico_m3':
        return [
          { label: 'Dashboard', href: '/medico-m3/dashboard', icon: FaUserMd },
          { label: 'Mi Agenda', href: '/medico-m3/agenda', icon: FaCalendar },
          { label: 'Mis Pacientes', href: '/medico-m3/pacientes', icon: FaUser }
        ];
      
      case 'admin_ministro_salud':
      case 'admin_ministro':
        return [
          { label: 'Dashboard', href: '/admin-ministro/dashboard', icon: FaHospital },
          { label: 'Establecimientos', href: '/admin-ministro/establecimientos', icon: FaHospital },
          { label: 'Seguimiento Pacientes', href: '/admin-ministro/seguimiento-pacientes', icon: FaUser }
        ];
      
      case 'admin_establecimiento':
        return [
          { label: 'Dashboard', href: '/admin-establecimiento/dashboard', icon: FaHospital },
          { label: 'Médicos', href: '/admin-establecimiento/medicos', icon: FaUserMd }
        ];
      
      case 'paciente':
        return [
          { label: 'Mi Panel', href: '/paciente/dashboard', icon: FaUser },
          { label: 'Mis Turnos', href: '/paciente/mis-turnos', icon: FaUser },
          { label: 'Mi Historial', href: '/paciente/mi-historial', icon: FaUser }
        ];
      
      default:
        return [];
    }
  };
  
  const menuItems = getMenuItems();
  
  const handleLogout = () => {
    logout();
    navigate('/login');
  };
  
  const getRolLabel = () => {
    const rol = user?.cliente_actual?.rol || 'paciente';
    const labels = {
      'medico_m1': 'Médico M1',
      'medico_m2': 'Médico M2', 
      'medico_m3': 'Médico M3',
      'admin_ministro_salud': 'Admin Ministro',
      'admin_establecimiento': 'Admin Establecimiento',
      'paciente': 'Paciente'
    };
    return labels[rol] || 'Usuario';
  };
  
  const getRolColor = () => {
    const rol = user?.cliente_actual?.rol || 'paciente';
    const colors = {
      'medico_m1': 'blue',
      'medico_m2': 'cyan',
      'medico_m3': 'purple',
      'admin_ministro_salud': 'red',
      'admin_establecimiento': 'orange',
      'paciente': 'green'
    };
    return colors[rol] || 'gray';
  };
  
  return (
    <Box>
      <Flex
        bg={useColorModeValue('white', 'gray.800')}
        color={useColorModeValue('gray.600', 'white')}
        minH={'60px'}
        py={{ base: 2 }}
        px={{ base: 4 }}
        borderBottom={1}
        borderStyle={'solid'}
        borderColor={useColorModeValue('gray.200', 'gray.900')}
        align={'center'}
      >
        <Flex
          flex={{ base: 1, md: 'auto' }}
          ml={{ base: -2 }}
          display={{ base: 'flex', md: 'none' }}
        >
          <IconButton
            onClick={onToggle}
            icon={isOpen ? <CloseIcon w={3} h={3} /> : <HamburgerIcon w={5} h={5} />}
            variant={'ghost'}
            aria-label={'Toggle Navigation'}
          />
        </Flex>
        
        <Flex flex={{ base: 1 }} justify={{ base: 'center', md: 'start' }}>
          <Text
            textAlign={useBreakpointValue({ base: 'center', md: 'left' })}
            fontFamily={'heading'}
            color={useColorModeValue('gray.800', 'white')}
            fontSize={{ base: 'lg', md: 'xl' }}
            fontWeight="bold"
          >
            ETHE - Sistema Médico
          </Text>
        </Flex>
        
        <Stack
          flex={{ base: 1, md: 0 }}
          justify={'flex-end'}
          direction={'row'}
          spacing={6}
        >
          {/* Desktop Navigation */}
          <Stack direction={'row'} spacing={4} display={{ base: 'none', md: 'flex' }}>
            {menuItems.map((item) => (
              <Button
                key={item.label}
                as={Link}
                href={item.href}
                variant="ghost"
                size="sm"
                leftIcon={<item.icon />}
                colorScheme={location.pathname === item.href ? 'blue' : 'gray'}
                onClick={() => navigate(item.href)}
              >
                {item.label}
              </Button>
            ))}
          </Stack>
          
          {/* User Menu */}
          <Menu>
            <MenuButton
              as={Button}
              rounded={'full'}
              variant={'link'}
              cursor={'pointer'}
              minW={0}
            >
              <Avatar size={'sm'} name={user?.nombre} />
            </MenuButton>
            <MenuList>
              <MenuItem>
                <Text fontSize="sm" fontWeight="bold">
                  {user?.nombre} {user?.apellido}
                </Text>
              </MenuItem>
              <MenuItem>
                <Badge colorScheme={getRolColor()} fontSize="xs">
                  {getRolLabel()}
                </Badge>
              </MenuItem>
              <MenuDivider />
              <MenuItem icon={<FaCog />} onClick={() => navigate('/perfil')}>
                Mi Perfil
              </MenuItem>
              <MenuItem icon={<FaSignOutAlt />} onClick={handleLogout}>
                Cerrar Sesión
              </MenuItem>
            </MenuList>
          </Menu>
        </Stack>
      </Flex>
      
      {/* Mobile Navigation */}
      <Collapse in={isOpen} animateOpacity>
        <Box
          bg={useColorModeValue('white', 'gray.800')}
          p={4}
          display={{ md: 'none' }}
        >
          <Stack spacing={4}>
            {menuItems.map((item) => (
              <Button
                key={item.label}
                as={Link}
                href={item.href}
                variant="ghost"
                size="md"
                leftIcon={<item.icon />}
                colorScheme={location.pathname === item.href ? 'blue' : 'gray'}
                onClick={() => {
                  navigate(item.href);
                  onToggle();
                }}
                justifyContent="flex-start"
              >
                {item.label}
              </Button>
            ))}
            <Divider />
            <Button
              variant="ghost"
              size="md"
              leftIcon={<FaCog />}
              onClick={() => {
                navigate('/perfil');
                onToggle();
              }}
              justifyContent="flex-start"
            >
              Mi Perfil
            </Button>
            <Button
              variant="ghost"
              size="md"
              leftIcon={<FaSignOutAlt />}
              onClick={() => {
                handleLogout();
                onToggle();
              }}
              justifyContent="flex-start"
              colorScheme="red"
            >
              Cerrar Sesión
            </Button>
          </Stack>
        </Box>
      </Collapse>
    </Box>
  );
};

export default ETHENavbar;
