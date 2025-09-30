// src/components/forms/TurnoSelector.jsx
import React from 'react';
import {
  FormControl, FormLabel, Select, Input, useColorModeValue, Stack, useBreakpointValue, Text
} from '@chakra-ui/react';

const LABELS = {
  x1: "Individual",
  x2: "2 Personas",
  x3: "3 Personas",
  x4: "4 Personas",
};

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
  // 👇 nuevas props para el Día
  day,                 // string "YYYY-MM-DD"
  onDayChange,         // fn(e.target.value)
  minDay,              // string "YYYY-MM-DD"
  maxDay,              // string "YYYY-MM-DD"
  diasDisponibles = [], // Nueva prop para días disponibles del profesor
  disabled = false,
}) => {
  const inputBg = useColorModeValue('white', 'gray.700');
  const inputBorder = useColorModeValue('gray.300', 'blue.400');
  const textColor = useColorModeValue('gray.800', 'white');
  const mutedText = useColorModeValue('gray.600', 'gray.400');
  const isMobile = useBreakpointValue({ base: true, md: false });

  const labelTipo = (t) => (t?.nombre) || LABELS[t?.codigo] || "Tipo";

  return (
    <Stack
      direction={{ base: 'column', md: 'row' }}
      spacing={4}
      align={{ base: 'stretch', md: 'end' }}
      mb={6}
      w="100%"
    >
      {/* Sede */}
      <FormControl flex={1} minW={0}>
        <FormLabel color={mutedText}>Sede</FormLabel>
        <Select
          value={sedeId}
          placeholder="Seleccionar sede"
          onChange={(e) => {
            onSedeChange?.(e.target.value);
            onTipoClaseChange?.(""); // limpia tipo al cambiar sede
          }}
          bg={inputBg}
          color={textColor}
          borderColor={inputBorder}
          rounded="md"
          w="100%"
          size={{ base: 'md', md: 'sm' }}
        >
          {sedes.map((s) => (
            <option key={s.id} value={String(s.id)}>
              {s.nombre}
            </option>
          ))}
        </Select>
      </FormControl>

      {/* Profesor */}
      <FormControl flex={1} minW={0} isDisabled={!sedeId || disabled}>
        <FormLabel color={mutedText}>Profesor</FormLabel>
        <Select
          value={profesorId}
          placeholder="Seleccionar profesor"
          onChange={(e) => onProfesorChange?.(e.target.value)}
          bg={inputBg}
          color={textColor}
          borderColor={inputBorder}
          rounded="md"
          w="100%"
          size={{ base: 'md', md: 'sm' }}
        >
          {profesores.map((p) => (
            <option key={p.id} value={String(p.id)}>
              {p.nombre_publico || p.nombre}
            </option>
          ))}
        </Select>
      </FormControl>

      {/* Tipo de Clase */}
      <FormControl
        flex={1}
        minW={0}
        isDisabled={!sedeId || tiposClase.length === 0 || disabled}
      >
        <FormLabel color={mutedText}>Tipo de Clase</FormLabel>
        <Select
          value={tipoClaseId}
          placeholder={tiposClase.length > 0 ? "Seleccionar tipo" : "No hay tipos disponibles"}
          onChange={(e) => onTipoClaseChange?.(e.target.value)}
          bg={inputBg}
          color={textColor}
          borderColor={inputBorder}
          rounded="md"
          w="100%"
          size={{ base: 'md', md: 'sm' }}
        >
          {tiposClase.map((t) => (
            <option key={t.id} value={String(t.id)}>
              {labelTipo(t)} - ${t.precio}
            </option>
          ))}
        </Select>
      </FormControl>

      {/* Día (solo mobile) */}
      {isMobile && (
        <FormControl flex={1} minW={0} isDisabled={!profesorId || disabled}>
          <FormLabel color={mutedText}>
            Día
            {profesorId && diasDisponibles.length > 0 && (
              <Text as="span" fontSize="xs" color={mutedText} ml={2}>
                (solo días disponibles)
              </Text>
            )}
          </FormLabel>
          <Input
            type="date"
            value={day || ""}
            onChange={(e) => onDayChange?.(e.target.value)}
            min={minDay}
            max={maxDay}
            bg={inputBg}
            color={textColor}
            borderColor={inputBorder}
            rounded="md"
            w="100%"
            size={{ base: 'md', md: 'sm' }}
          />
        </FormControl>
      )}
    </Stack>
  );
};

export default TurnoSelector;
