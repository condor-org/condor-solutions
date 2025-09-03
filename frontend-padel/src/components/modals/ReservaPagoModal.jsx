// src/components/modals/ReservaPagoModal.jsx

import React, { useEffect, useMemo,useRef } from "react";
import {
  Box,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalCloseButton,
  ModalBody,
  ModalFooter,
  Text,
  Button,
  Icon,
  Input,
  useColorModeValue,
  Flex,
  Switch,
  FormControl,
  FormLabel
} from "@chakra-ui/react";
import { FaCalendarAlt, FaClock, FaTrash } from "react-icons/fa";
import CountdownClock from "../ui/CountdownClock.jsx";
import { CopyIcon } from "@chakra-ui/icons";
import { useToast, Tooltip, IconButton } from "@chakra-ui/react";



const LABELS = {
  x1: "Individual",
  x2: "2 Personas",
  x3: "3 Personas",
  x4: "4 Personas",
};

const ReservaPagoModal = ({
  alias, 
  cbuCvu,
  isOpen,
  onClose,
  turno,        // Puede venir como evento (con start Date) o como {fecha, hora} (abono)
  configPago,
  tipoClase,    // {codigo, nombre?, precio}
  archivo,
  onArchivoChange,
  onRemoveArchivo,
  onConfirmar,
  loading,
  tiempoRestante,
  bonificaciones = [],
  usarBonificado,
  setUsarBonificado
}) => {
  const modalBg = useColorModeValue("white", "gray.900");
  const modalText = useColorModeValue("gray.800", "white");
  const resumenBg = useColorModeValue("green.50", "green.900");
  const resumenBorder = useColorModeValue("green.400", "green.500");
  const resumenText = useColorModeValue("green.800", "green.200");
  const dropzoneBg = useColorModeValue("gray.100", "#232b34");
  const dropzoneHover = useColorModeValue("gray.200", "#243039");
  const dropzoneBorder = useColorModeValue("green.500", "#27ae60");

  const tieneBonos = bonificaciones.length > 0;
  useEffect(() => {
    if (!tieneBonos && usarBonificado) {
      setUsarBonificado(false);
    }
  }, [tieneBonos, usarBonificado, setUsarBonificado]);

  const segundos = Number(tiempoRestante || configPago?.tiempo_maximo_minutos * 60 || 900);

  // Normaliza fecha/hora para UI (turno de calendario o abono)
  const fechaObj = useMemo(() => {
    if (!turno) return null;
    const s = turno.start;
    if (s instanceof Date) return s;
    if (typeof s === "string") {
      const d = new Date(s);
      return isNaN(d.getTime()) ? null : d;
    }
    return null;
  }, [turno]);

  const fechaTexto = useMemo(() => {
    if (!turno) return null;
    if (fechaObj) {
      return fechaObj.toLocaleDateString("es-AR", { weekday: "long", day: "numeric", month: "long" });
    }
    if (typeof turno.fecha === "string") return turno.fecha; // p.ej. "Mes 8/2025"
    return null;
  }, [turno, fechaObj]);

  const horaTexto = useMemo(() => {
    if (!turno) return null;
    if (fechaObj) {
      return fechaObj.toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit" });
    }
    if (typeof turno.hora === "string") {
      return (turno.hora || "").slice(0,5); // "08:00"
    }
    return null;
  }, [turno, fechaObj]);

  const nombreTipo = (tipoClase?.nombre) || LABELS[tipoClase?.codigo] || "—";

  const toast = useToast();
const hiddenInputRef = useRef(null);

const copyText = async (text, label = "Texto") => {
  try {
    if (navigator?.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
    } else {
      // Fallback: input oculto + execCommand
      const input = hiddenInputRef.current || document.createElement("input");
      if (!hiddenInputRef.current) {
        input.style.position = "fixed";
        input.style.opacity = "0";
        document.body.appendChild(input);
        hiddenInputRef.current = input;
      }
      input.value = text;
      input.select();
      document.execCommand("copy");
    }
    toast({ title: `${label} copiado`, status: "success", duration: 1800, isClosable: true });
    console.debug(`[ReservaPagoModal] Copiado a portapapeles: ${label}`);
  } catch (err) {
    console.error(`[ReservaPagoModal] Error al copiar ${label}:`, err);
    toast({ title: `No se pudo copiar el ${label.toLowerCase()}`, status: "error", duration: 2500, isClosable: true });
  }
};


  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      isCentered
      size={{ base: "xs", sm: "sm", md: "lg" }}
      motionPreset="slideInBottom"
    >
      <ModalOverlay />
      <ModalContent
        bg={modalBg}
        color={modalText}
        px={{ base: 4, md: 6 }}
        py={{ base: 3, md: 4 }}
        borderRadius="2xl"
      >
        <ModalHeader fontWeight="bold" fontSize={{ base: "md", md: "lg" }} color="blue.300">
          Confirmar reserva
        </ModalHeader>
        <ModalCloseButton />

        <ModalBody>
          {(fechaTexto || horaTexto) && (
            <Box
              mb={{ base: 4, md: 5 }}
              border="2px solid"
              borderColor={resumenBorder}
              bg={resumenBg}
              color={resumenText}
              borderRadius="md"
              px={{ base: 3, md: 4 }}
              py={{ base: 2, md: 3 }}
              wordBreak="break-word"
            >
              {fechaTexto && (
                <Flex align="center" gap={{ base: 2, md: 3 }} wrap="wrap">
                  <Icon as={FaCalendarAlt} boxSize={{ base: 4, md: 5 }} />
                  <Text fontSize={{ base: "sm", md: "md" }} whiteSpace="normal">
                    <b>Día:</b> {fechaTexto}
                  </Text>
                </Flex>
              )}
              {horaTexto && (
                <Flex align="center" gap={{ base: 2, md: 3 }} mt={2} wrap="wrap">
                  <Icon as={FaClock} boxSize={{ base: 4, md: 5 }} />
                  <Text fontSize={{ base: "sm", md: "md" }} whiteSpace="normal">
                    <b>Hora:</b> {horaTexto} hs
                  </Text>
                </Flex>
              )}
            </Box>
          )}

          {tipoClase && (
            <Box mb={{ base: 4, md: 6 }} wordBreak="break-word">
              <Text fontSize={{ base: "sm", md: "md" }}>
                <b>Tipo de clase:</b> {nombreTipo}
              </Text>
              {"precio" in tipoClase && (
                <Text fontSize={{ base: "sm", md: "md" }}>
                  <b>Monto:</b> ${tipoClase.precio}
                </Text>
              )}
              {alias && (
              <Flex align="center" gap={2} wrap="wrap" mt={1}>
                <Text fontSize={{ base: "sm", md: "md" }}>
                  <b>Alias:</b> {alias}
                </Text>
                <Tooltip label="Copiar alias" hasArrow>
                  <IconButton
                    aria-label="Copiar alias"
                    size="xs"
                    variant="ghost"
                    icon={<CopyIcon />}
                    onClick={() => copyText(alias, "Alias")}
                  />
                </Tooltip>
              </Flex>
            )}
              {cbuCvu && (
                <Flex align="center" gap={2} wrap="wrap" mt={1}>
                  <Text fontSize={{ base: "sm", md: "md" }}>
                    <b>CBU/CVU:</b> {cbuCvu}
                  </Text>
                  <Tooltip label="Copiar CBU/CVU" hasArrow>
                    <IconButton
                      aria-label="Copiar CBU/CVU"
                      size="xs"
                      variant="ghost"
                      icon={<CopyIcon />}
                      onClick={() => copyText(cbuCvu, "CBU/CVU")}
                    />
                  </Tooltip>
                </Flex>
              )}
            </Box>
          )}

          <CountdownClock
            segundosTotales={segundos}
            size="md"
            showLabel={true}
            colorScheme="green"
            onFinalizar={() => {
              onClose();
              alert("⏱ El tiempo para confirmar la reserva ha finalizado.");
            }}
          />

          {tieneBonos && (
            <Box
              mt={6}
              mb={4}
              p={{ base: 3, md: 4 }}
              borderRadius="md"
              bg={`${resumenBg}88`}
              border="1px solid"
              borderColor={resumenBorder}
              wordBreak="break-word"
            >
              <Text fontWeight="medium" mb={2} fontSize={{ base: "sm", md: "md" }}>
                Tenés {bonificaciones.length} turno{bonificaciones.length > 1 ? "s" : ""} bonificado{bonificaciones.length > 1 ? "s" : ""}.
              </Text>
              <FormControl display="flex" alignItems="center">
                <FormLabel htmlFor="usarBonificado" mb="0" fontSize={{ base: "sm", md: "md" }}>
                  ¿Querés usar uno para esta reserva?
                </FormLabel>
                <Switch
                  id="usarBonificado"
                  isChecked={usarBonificado}
                  onChange={(e) => setUsarBonificado(e.target.checked)}
                  colorScheme="teal"
                />
              </FormControl>
            </Box>
          )}

          {!usarBonificado && (
            <Box
              as="label"
              htmlFor="archivo"
              border="2px dashed"
              borderColor={dropzoneBorder}
              bg={dropzoneBg}
              px={{ base: 3, md: 4 }}
              py={{ base: 4, md: 4 }}
              minH="60px"
              rounded="lg"
              w="100%"
              cursor="pointer"
              display="flex"
              alignItems="center"
              justifyContent="center"
              textAlign="center"
              _hover={{ borderColor: "green.400", bg: dropzoneHover }}
              mt={{ base: 3, md: 4 }}
              mb={{ base: 2, md: 3 }}
            >
              <Input
                id="archivo"
                type="file"
                display="none"
                onChange={e => onArchivoChange(e.target.files[0])}
              />
              <Text color="gray.500" fontSize={{ base: "xs", md: "sm" }} fontWeight="medium" wordBreak="break-word">
                {archivo ? `📄 ${archivo.name}` : "📎 Subí el comprobante de pago"}
              </Text>
            </Box>
          )}

          {!usarBonificado && archivo && (
            <Button
              size={{ base: "sm", md: "sm" }}
              leftIcon={<FaTrash />}
              colorScheme="red"
              variant="ghost"
              onClick={onRemoveArchivo}
              mb={2}
            >
              Quitar archivo
            </Button>
          )}

          <Text fontSize={{ base: "xs", md: "sm" }} color="gray.500" mt={{ base: 4, md: 6 }} wordBreak="break-word">
            <b>📋 Política de reserva:</b> Toda reserva debe incluir comprobante de pago.
            Las cancelaciones sólo se permiten con <b>mínimo 24 horas de anticipación</b>.
            Si no se confirma el pago antes del fin del contador, el turno será liberado automáticamente.
          </Text>
        </ModalBody>

        <ModalFooter
          // ✅ en pantallas chicas, permitimos wrap para que no se rompa
          flexWrap={{ base: "wrap", md: "nowrap" }}
          gap={{ base: 2, md: 3 }}
        >
          <Button
            colorScheme="blue"
            mr={{ base: 0, md: 3 }}
            isLoading={loading}
            onClick={onConfirmar}
            size={{ base: "sm", md: "md" }}
            flexShrink={0}
          >
            Confirmar reserva
          </Button>
          <Button
            variant="ghost"
            onClick={onClose}
            size={{ base: "sm", md: "md" }}
            flexShrink={0}
          >
            Cancelar
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default ReservaPagoModal;
