import React from "react";
import {
  Box,
  Button,
  VStack,
  Heading,
  useColorModeValue,
  IconButton,
  Collapse,
  HStack,
  Divider,
} from "@chakra-ui/react";
import { HamburgerIcon, CloseIcon } from "@chakra-ui/icons";
import { useNavigate, useLocation } from "react-router-dom";
import { useDisclosure } from "@chakra-ui/react";

const Sidebar = ({ links }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { isOpen, onToggle, onClose } = useDisclosure();

  // Colors
  const bg = useColorModeValue("gray.100", "gray.900");
  const textColor = useColorModeValue("gray.800", "gray.200");
  const headingColor = useColorModeValue("gray.900", "white");
  const buttonBg = useColorModeValue("blue.100", "gray.800");
  const buttonHoverBg = useColorModeValue("blue.200", "gray.700");
  const borderRight = useColorModeValue("gray.200", "gray.700");

  const Item = ({ label, path }) => {
    const active = location.pathname === path;
    return (
      <Button
        key={path}
        onClick={() => {
          navigate(path);
          onClose(); // cerrar el menú en mobile al navegar
        }}
        variant={active ? "solid" : "outline"}
        colorScheme="blue"
        justifyContent="flex-start"
        fontSize={{ base: "sm", md: "md" }}
        bg={active ? "blue.600" : buttonBg}
        color="white"
        _hover={{
          bg: active ? "blue.700" : buttonHoverBg,
          color: "white",
        }}
        borderColor="blue.600"
        borderWidth={active ? "2px" : "1px"}
        shadow={active ? "md" : "none"}
        transition="background 0.2s, color 0.2s"
        w="100%"
        whiteSpace="normal"
        textAlign="left"
        aria-current={active ? "page" : undefined}
      >
        {label}
      </Button>
    );
  };

  return (
    <Box
      // Mobile: barra arriba; Desktop: sidebar a la izquierda
      bg={bg}
      color={textColor}
      w={{ base: "100%", md: "56" }}
      minH={{ base: "auto", md: "100vh" }}
      px={{ base: 4, md: 4 }}
      py={{ base: 3, md: 6 }}
      position={{ base: "static", md: "sticky" }}
      top={{ base: "auto", md: 0 }}
      minW={0}
      boxShadow={{ base: "sm", md: "none" }}
      borderRightWidth={{ base: "0", md: "1px" }}
      borderRightColor={{ base: "transparent", md: borderRight }}
      zIndex={2}
    >
      {/* Header (siempre visible). En mobile incluye toggle */}
      <HStack justify="space-between" align="center" mb={{ base: 2, md: 6 }}>
        <Heading size={{ base: "sm", md: "md" }} color={headingColor}>
          Menú Admin
        </Heading>

        {/* Toggle sólo en mobile */}
        <IconButton
          display={{ base: "inline-flex", md: "none" }}
          size="sm"
          variant="ghost"
          aria-label={isOpen ? "Cerrar menú" : "Abrir menú"}
          icon={isOpen ? <CloseIcon boxSize={3} /> : <HamburgerIcon boxSize={5} />}
          onClick={onToggle}
          aria-expanded={isOpen}
        />
      </HStack>

      {/* Divider sutil en mobile */}
      <Divider display={{ base: "block", md: "none" }} mb={2} />

      {/* Contenido:
          - Mobile: Collapse vertical con scroll si es largo
          - Desktop: Lista fija vertical con scroll propio si excede la pantalla */}
      <Box
        overflowY={{ base: "visible", md: "auto" }}
        maxH={{ base: "none", md: "calc(100vh - 88px)" }} // deja espacio para el header del sidebar
        pr={{ md: 1 }}
      >
        {/* Mobile: colapsable */}
        <Collapse in={isOpen} animateOpacity style={{ overflow: "visible" }}>
          <VStack
            spacing={{ base: 3, md: 4 }}
            align="stretch"
            display={{ base: "flex", md: "none" }}
            mt={{ base: 2, md: 0 }}
          >
            {links.map((link) => (
              <Item key={link.path} {...link} />
            ))}
          </VStack>
        </Collapse>

        {/* Desktop: siempre visible */}
        <VStack
          spacing={{ base: 3, md: 4 }}
          align="stretch"
          display={{ base: "none", md: "flex" }}
        >
          {links.map((link) => (
            <Item key={link.path} {...link} />
          ))}
        </VStack>
      </Box>
    </Box>
  );
};

export default Sidebar;
