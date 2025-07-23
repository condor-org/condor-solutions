import React, { useEffect, useState } from "react";
import {
  Box,
  Text,
  useColorModeValue,
  VStack,
  Badge
} from "@chakra-ui/react";

const CountdownClock = ({
  segundosTotales = 180,
  onFinalizar,
  size = "md",
  showLabel = true,
  colorScheme = "blue"
}) => {
  const [timeLeft, setTimeLeft] = useState(() => {
    const inicial = Number(segundosTotales);
    return Number.isFinite(inicial) && inicial >= 0 ? inicial : 180;
  });

  const bg = useColorModeValue("gray.100", "gray.800");
  const color = useColorModeValue(`${colorScheme}.600`, `${colorScheme}.300`);
  const borderColor = useColorModeValue(`${colorScheme}.300`, `${colorScheme}.500`);

  useEffect(() => {
    if (!Number.isFinite(timeLeft)) return;

    if (timeLeft <= 0) {
      if (onFinalizar) onFinalizar();
      return;
    }

    const interval = setInterval(() => {
      setTimeLeft((prev) => prev - 1);
    }, 1000);

    return () => clearInterval(interval);
  }, [timeLeft]);

  const minutos = Math.floor(timeLeft / 60);
  const segundos = timeLeft % 60;

  const labelFontSize = size === "lg" ? "md" : size === "sm" ? "xs" : "sm";
  const clockFontSize = size === "lg" ? "3xl" : size === "sm" ? "md" : "xl";
  const boxPadding = size === "lg" ? 5 : size === "sm" ? 3 : 4;

  return (
    <VStack spacing={2} align="center" justify="center" textAlign="center">
      {showLabel && (
        <Text fontSize={labelFontSize} fontWeight="medium" color="gray.500">
          ⏳ Tiempo restante
        </Text>
      )}
      <Box
        bg={bg}
        border="2px solid"
        borderColor={borderColor}
        rounded="md"
        px={boxPadding}
        py={boxPadding - 1}
        fontSize={clockFontSize}
        fontWeight="bold"
        fontFamily="monospace"
        color={color}
        boxShadow="md"
        minW="120px"
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
