// src/components/ui/CountdownClock.jsx

import React, { useEffect, useState } from "react";
import {
  Box,
  Text,
  useColorModeValue,
  VStack,
  Badge
} from "@chakra-ui/react";

const CountdownClock = ({
  segundosTotales = 900,
  onFinalizar,
  size = "md",
  showLabel = true,
  colorScheme = "blue"
}) => {
  const normalize = (v) => {
    const n = Number(v);
    return Number.isFinite(n) && n >= 0 ? n : 900;
  };

  const [timeLeft, setTimeLeft] = useState(() => normalize(segundosTotales));

  // ✅ Si cambia el prop, reseteamos el contador de forma segura
  useEffect(() => {
    setTimeLeft(normalize(segundosTotales));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [segundosTotales]);

  const bg = useColorModeValue("gray.100", "gray.800");
  const color = useColorModeValue(`${colorScheme}.600`, `${colorScheme}.300`);
  const borderColor = useColorModeValue(`${colorScheme}.300`, `${colorScheme}.500`);

  useEffect(() => {
    if (!Number.isFinite(timeLeft)) return;
    if (timeLeft <= 0) {
      onFinalizar?.();
      return;
    }
    const interval = setInterval(() => {
      setTimeLeft((prev) => prev - 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [timeLeft, onFinalizar]);

  const minutos = Math.floor(timeLeft / 60);
  const segundos = timeLeft % 60;

  const labelFontSize = size === "lg" ? "md" : size === "sm" ? "xs" : "sm";
  const clockFontSize = size === "lg" ? "3xl" : size === "sm" ? "md" : "xl";
  const boxPaddingX = size === "lg" ? 5 : size === "sm" ? 3 : 4;
  const boxPaddingY = size === "lg" ? 4 : size === "sm" ? 2 : 3;

  return (
    <VStack spacing={{ base: 2, md: 2 }} align="center" justify="center" textAlign="center" w="100%" minW={0}>
      {showLabel && (
        <Text fontSize={{ base: labelFontSize, md: labelFontSize }} fontWeight="medium" color="gray.500" noOfLines={1}>
          ⏳ Tiempo restante
        </Text>
      )}
      <Box
        bg={bg}
        border="2px solid"
        borderColor={borderColor}
        rounded="md"
        px={boxPaddingX}
        py={boxPaddingY}
        fontSize={{ base: clockFontSize, md: clockFontSize }}
        fontWeight="bold"
        fontFamily="monospace"
        color={color}
        boxShadow="md"
        minW="120px"
        // ✅ evita overflow visual en contenedores angostos
        wordBreak="break-word"
      >
        {String(minutos).padStart(2, "0")}:{String(segundos).padStart(2, "0")}
      </Box>
      {timeLeft <= 0 && (
        <Badge mt={2} colorScheme="red">
          ⌛ Tu tiempo ha finalizado
        </Badge>
      )}
    </VStack>
  );
};

export default CountdownClock;
