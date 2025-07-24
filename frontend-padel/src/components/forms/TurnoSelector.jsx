// src/components/forms/TurnoSelector.jsx

import React from 'react';
import {
  Box, FormControl, FormLabel, Select, useColorModeValue, Stack
} from '@chakra-ui/react';

const TurnoSelector = ({
  sedes = [],
  profesores = [],
  sedeId,
  profesorId,
  onSedeChange,
  onProfesorChange,
  disabled = false,
}) => {
  const inputBg = useColorModeValue('white', 'gray.700');
  const inputBorder = useColorModeValue('gray.300', 'blue.400');
  const textColor = useColorModeValue('gray.800', 'white');
  const mutedText = useColorModeValue('gray.600', 'gray.400');

  return (
    <Stack
      direction={{ base: 'column', md: 'row' }}
      spacing={4}
      align={{ base: 'stretch', md: 'end' }}
      mb={6}
    >
      <FormControl flex={1}>
        <FormLabel color={mutedText}>Sede</FormLabel>
        <Select
          value={sedeId}
          placeholder="Seleccionar sede"
          onChange={(e) => {
            onSedeChange?.(e.target.value);
          }}
          bg={inputBg}
          color={textColor}
          borderColor={inputBorder}
          rounded="md"
        >
          {sedes.map((s) => (
            <option key={s.id} value={s.id}>
              {s.nombre}
            </option>
          ))}
        </Select>
      </FormControl>

      <FormControl flex={1} isDisabled={!sedeId || disabled}>
        <FormLabel color={mutedText}>Profesor</FormLabel>
        <Select
          value={profesorId}
          placeholder="Seleccionar profesor"
          onChange={(e) => {
            onProfesorChange?.(e.target.value);
          }}
          bg={inputBg}
          color={textColor}
          borderColor={inputBorder}
          rounded="md"
        >
          {profesores.map((p) => (
            <option key={p.id} value={p.id}>
              {p.nombre_publico}
            </option>
          ))}
        </Select>
      </FormControl>
    </Stack>
  );
};

export default TurnoSelector;
