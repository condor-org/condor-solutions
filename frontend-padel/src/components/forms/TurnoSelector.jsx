// src/components/forms/TurnoSelector.jsx

import React from 'react';
import {
  FormControl, FormLabel, Select, useColorModeValue, Stack
} from '@chakra-ui/react';

const TurnoSelector = ({
  sedes = [],
  profesores = [],
  tiposClase = [],
  sedeId,
  profesorId,
  tipoClaseId,
  onSedeChange,
  onProfesorChange,
  onTipoClaseChange,
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
      {/* Sede */}
      <FormControl flex={1}>
        <FormLabel color={mutedText}>Sede</FormLabel>
        <Select
          value={sedeId}
          placeholder="Seleccionar sede"
          onChange={(e) => {
            onSedeChange?.(e.target.value);
            onTipoClaseChange?.(""); // 🔹 Limpia tipo de clase al cambiar sede
          }}
          bg={inputBg}
          color={textColor}
          borderColor={inputBorder}
          rounded="md"
        >
          {sedes.map((s) => (
            <option key={s.id} value={String(s.id)}>
              {s.nombre}
            </option>
          ))}
        </Select>
      </FormControl>

      {/* Profesor */}
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
            <option key={p.id} value={String(p.id)}>
              {p.nombre_publico || p.nombre}
            </option>
          ))}
        </Select>
      </FormControl>

      {/* Tipo de Clase */}
      <FormControl flex={1} isDisabled={!sedeId || tiposClase.length === 0 || disabled}>
        <FormLabel color={mutedText}>Tipo de Clase</FormLabel>
        <Select
          value={tipoClaseId}
          placeholder={tiposClase.length > 0 ? "Seleccionar tipo" : "No hay tipos disponibles"}
          onChange={(e) => {
            onTipoClaseChange?.(e.target.value);
          }}
          bg={inputBg}
          color={textColor}
          borderColor={inputBorder}
          rounded="md"
        >
          {tiposClase.map((t) => (
            <option key={t.id} value={String(t.id)}>
              {t.nombre} - ${t.precio}
            </option>
          ))}
        </Select>
      </FormControl>
    </Stack>
  );
};

export default TurnoSelector;
