// src/components/layout/Sidebar.jsx

import React from 'react';
import { Box, Button, VStack, Heading, useColorModeValue } from '@chakra-ui/react';
import { useNavigate, useLocation } from 'react-router-dom';

const Sidebar = ({ links }) => {
  const navigate = useNavigate();
  const location = useLocation();

  const bg = useColorModeValue('gray.100', 'gray.900');
  const textColor = useColorModeValue('gray.800', 'gray.200');
  const headingColor = useColorModeValue('gray.900', 'white');
  const buttonBg = useColorModeValue('blue.100', 'gray.800');
  const buttonHoverBg = useColorModeValue('blue.200', 'gray.700');

  return (
    <Box
      bg={bg}
      color={textColor}
      // ✅ Responsive: full width en mobile, sidebar fija en md+
      w={{ base: '100%', md: '56' }}
      minH={{ base: 'auto', md: '100vh' }}
      px={{ base: 4, md: 4 }}
      py={{ base: 4, md: 6 }}
      // Sticky sólo en pantallas medianas en adelante
      position={{ base: 'static', md: 'sticky' }}
      top={{ base: 'auto', md: 0 }}
      // Evita que su contenido fuerce ancho extra
      minW={0}
      boxShadow={{ base: 'sm', md: 'none' }}
      borderRightWidth={{ base: '0', md: '1px' }}
      borderRightColor={{ base: 'transparent', md: 'gray.200' }}
    >
      <Heading
        size={{ base: 'sm', md: 'md' }}
        color={headingColor}
        mb={{ base: 4, md: 6 }}
      >
        Menú Admin
      </Heading>

      <VStack spacing={{ base: 3, md: 4 }} align="stretch">
        {links.map(({ label, path }) => {
          const active = location.pathname === path;
          return (
            <Button
              key={path}
              onClick={() => navigate(path)}
              variant={active ? 'solid' : 'outline'}
              colorScheme="blue"
              justifyContent="flex-start"
              fontSize={{ base: 'sm', md: 'md' }}
              bg={active ? 'blue.600' : buttonBg}
              color="white"
              _hover={{
                bg: active ? 'blue.700' : buttonHoverBg,
                color: 'white',
              }}
              borderColor="blue.600"
              borderWidth={active ? '2px' : '1px'}
              shadow={active ? 'md' : 'none'}
              transition="background 0.2s, color 0.2s"
              // ✅ Botón ocupa todo el ancho en mobile
              w={{ base: '100%', md: 'auto' }}
              // Evita que el texto largo rompa el layout
              whiteSpace="normal"
              textAlign="left"
            >
              {label}
            </Button>
          );
        })}
      </VStack>
    </Box>
  );
};

export default Sidebar;
