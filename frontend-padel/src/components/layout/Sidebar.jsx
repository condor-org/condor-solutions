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
    <Box bg={bg} color={textColor} w="56" minH="100vh" px={4} py={6}>
      <Heading size="md" color={headingColor} mb={6}>
        Menú Admin
      </Heading>
      <VStack spacing={4} align="stretch">
        {links.map(({ label, path }) => (
          <Button
            key={path}
            onClick={() => navigate(path)}
            variant={location.pathname === path ? "solid" : "outline"}
            colorScheme="blue"
            justifyContent="flex-start"
            fontSize="md"
            bg={location.pathname === path ? "blue.600" : buttonBg}
            color="white"
            _hover={{
              bg: location.pathname === path ? "blue.700" : buttonHoverBg,
              color: "white",
            }}
            borderColor="blue.600"
            borderWidth={location.pathname === path ? "2px" : "1px"}
            shadow={location.pathname === path ? "md" : "none"}
            transition="background 0.2s, color 0.2s"
          >
            {label}
          </Button>
        ))}
      </VStack>
    </Box>
  );
};

export default Sidebar;
