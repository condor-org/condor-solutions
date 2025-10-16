// src/components/modals/ReservaPagoModal.jsx
import React, { useEffect, useMemo, useRef, useState } from "react";
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
  Badge,
  Stack,
  HStack,
  RadioGroup,
  Radio,
  Tooltip,
  IconButton,
  useToast,
  Divider,
  Alert,
  AlertIcon,
} from "@chakra-ui/react";
import { FaCalendarAlt, FaClock, FaTrash } from "react-icons/fa";
import CountdownClock from "../ui/CountdownClock.jsx";
import { CopyIcon } from "@chakra-ui/icons";

const LABELS = { x1: "Individual", x2: "2 Personas", x3: "3 Personas", x4: "4 Personas" };

const ReservaPagoModal = ({
  alias,
  cbuCvu,
  isOpen,
  onClose,
  turno,               // evento (start: Date|string) o {fecha, hora}
  configPago,
  tipoClase,           // {codigo, nombre?, precio}
  archivo,
  onArchivoChange,
  onRemoveArchivo,
  onConfirmar,         // onConfirmar(selectedBonoId)
  loading,
  tiempoRestante,
  bonificaciones = [], // [{id, tipo_turno, valor, valido_hasta, motivo?}]
}) => {
  const modalBg = useColorModeValue("white", "gray.900");
  const modalText = useColorModeValue("gray.800", "white");
  const resumenBg = useColorModeValue("green.50", "green.900");
  const resumenBorder = useColorModeValue("green.400", "green.500");
  const resumenText = useColorModeValue("green.800", "green.200");
  const dropzoneBg = useColorModeValue("gray.100", "#232b34");
  const dropzoneHover = useColorModeValue("gray.200", "#243039");
  const dropzoneBorder = useColorModeValue("green.500", "#27ae60");
  const muted = useColorModeValue("gray.600", "gray.400");

  const [selectedBonoId, setSelectedBonoId] = useState(null);

  const segundos = Number(tiempoRestante || configPago?.tiempo_maximo_minutos * 60 || 900);

  // ---- Fecha/Hora
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
    if (fechaObj) return fechaObj.toLocaleDateString("es-AR", { weekday: "long", day: "numeric", month: "long" });
    if (typeof turno.fecha === "string") return turno.fecha;
    return null;
  }, [turno, fechaObj]);

  const horaTexto = useMemo(() => {
    if (!turno) return null;
    if (fechaObj) return fechaObj.toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit" });
    if (typeof turno.hora === "string") return (turno.hora || "").slice(0, 5);
    return null;
  }, [turno, fechaObj]);

  // ---- Cálculos
  const nombreTipo = (tipoClase?.nombre) || LABELS[tipoClase?.codigo] || "—";
  const precioClase = useMemo(() => Number(tipoClase?.precio ?? 0), [tipoClase]);

  const elegiblesOrdenados = useMemo(() => {
    const codigo = (tipoClase?.codigo || "").toLowerCase();
    return (bonificaciones || [])
      .filter((b) => (b?.tipo_turno || "").toLowerCase() === codigo)
      .slice()
      .sort((a, b) => {
        const va = a?.valido_hasta ? new Date(a.valido_hasta).getTime() : Infinity;
        const vb = b?.valido_hasta ? new Date(b.valido_hasta).getTime() : Infinity;
        return va - vb;
      });
  }, [bonificaciones, tipoClase]);

  useEffect(() => {
    setSelectedBonoId((prev) => (elegiblesOrdenados.some((b) => b.id === prev) ? prev : null));
  }, [elegiblesOrdenados]);

  const selectedBono = useMemo(
    () => elegiblesOrdenados.find((b) => b.id === selectedBonoId) || null,
    [elegiblesOrdenados, selectedBonoId]
  );

  const valorBono = useMemo(() => {
    const v = Number(selectedBono?.valor);
    return Number.isFinite(v) && v >= 0 ? v : 0;
  }, [selectedBono]);

  const valorRestante = useMemo(() => Math.max(0, precioClase - valorBono), [precioClase, valorBono]);

  const needsComprobante = valorRestante > 0;
  const confirmDisabled = loading || (needsComprobante && !archivo);

  // ---- Utils
  const toast = useToast();
  const hiddenInputRef = useRef(null);
  const copyText = async (text, label = "Texto") => {
    try {
      if (navigator?.clipboard?.writeText) await navigator.clipboard.writeText(text);
      else {
        const input = hiddenInputRef.current || document.createElement("input");
        if (!hiddenInputRef.current) {
          input.style.position = "fixed"; input.style.opacity = "0";
          document.body.appendChild(input); hiddenInputRef.current = input;
        }
        input.value = text; input.select(); document.execCommand("copy");
      }
      toast({ title: `${label} copiado`, status: "success", duration: 1800, isClosable: true });
    } catch (err) {
      console.error(`[ReservaPagoModal] copy ${label} error:`, err);
      toast({ title: `No se pudo copiar el ${label.toLowerCase()}`, status: "error", duration: 2500, isClosable: true });
    }
  };

  // ---- Render
  return (
    <Modal isOpen={isOpen} onClose={onClose} isCentered size={{ base: "xs", sm: "sm", md: "lg" }} motionPreset="slideInBottom">
      <ModalOverlay />
      <ModalContent bg={modalBg} color={modalText} px={{ base: 4, md: 6 }} py={{ base: 3, md: 4 }} borderRadius="2xl">
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
                  <Text fontSize={{ base: "sm", md: "md" }}><b>Día:</b> {fechaTexto}</Text>
                </Flex>
              )}
              {horaTexto && (
                <Flex align="center" gap={{ base: 2, md: 3 }} mt={2} wrap="wrap">
                  <Icon as={FaClock} boxSize={{ base: 4, md: 5 }} />
                  <Text fontSize={{ base: "sm", md: "md" }}><b>Hora:</b> {horaTexto} hs</Text>
                </Flex>
              )}
            </Box>
          )}

          {tipoClase && (
            <Box mb={{ base: 4, md: 5 }} wordBreak="break-word">
              <Text fontSize={{ base: "sm", md: "md" }}><b>Tipo de clase:</b> {nombreTipo}</Text>
              {"precio" in tipoClase && (
                <Text fontSize={{ base: "sm", md: "md" }}><b>Precio:</b> ${Number(precioClase).toLocaleString("es-AR")}</Text>
              )}
              {alias && (
                <Flex align="center" gap={2} wrap="wrap" mt={1}>
                  <Text fontSize={{ base: "sm", md: "md" }}><b>Alias:</b> {alias}</Text>
                  <Tooltip label="Copiar alias" hasArrow>
                    <IconButton aria-label="Copiar alias" size="xs" variant="ghost" icon={<CopyIcon />} onClick={() => copyText(alias, "Alias")} />
                  </Tooltip>
                </Flex>
              )}
              {cbuCvu && (
                <Flex align="center" gap={2} wrap="wrap" mt={1}>
                  <Text fontSize={{ base: "sm", md: "md" }}><b>CBU/CVU:</b> {cbuCvu}</Text>
                  <Tooltip label="Copiar CBU/CVU" hasArrow>
                    <IconButton aria-label="Copiar CBU/CVU" size="xs" variant="ghost" icon={<CopyIcon />} onClick={() => copyText(cbuCvu, "CBU/CVU")} />
                  </Tooltip>
                </Flex>
              )}
            </Box>
          )}

          <CountdownClock
            segundosTotales={segundos}
            size="md"
            showLabel
            colorScheme="green"
            onFinalizar={() => { onClose(); alert("⏱ El tiempo para confirmar la reserva ha finalizado."); }}
          />

          {/* Bonificaciones elegibles */}
          {!!elegiblesOrdenados.length && (
            <Box
              mt={{ base: 4, md: 5 }}
              mb={{ base: 3, md: 4 }}
              p={{ base: 3, md: 4 }}
              borderRadius="lg"
              bg={`${resumenBg}88`}
              border="1px solid"
              borderColor={resumenBorder}
            >
              <Text fontWeight="semibold" mb={2} fontSize={{ base: "sm", md: "md" }}>
                Bonificaciones disponibles para esta clase:
              </Text>

              <RadioGroup
                value={selectedBonoId ? String(selectedBonoId) : "none"}
                onChange={(val) => setSelectedBonoId(val === "none" ? null : Number(val))}
              >
                <Box maxH={{ base: "35vh", md: "none" }} overflowY={{ base: "auto", md: "visible" }} pr={{ base: 1, md: 0 }}>
                  <Stack spacing={1.5}>
                    <Box
                      as={Radio}
                      value="none"
                      borderRadius="md"
                      px={3}
                      py={2}
                      size="sm"
                      sx={{ ".chakra-radio__control": { w: 3, h: 3 } }}
                    >
                      No usar bonificación
                    </Box>

                    {elegiblesOrdenados.map((b) => {
                      const vence = b.valido_hasta && new Date(b.valido_hasta).toLocaleDateString("es-AR");
                      return (
                        <Box
                          key={b.id}
                          as={Radio}
                          value={String(b.id)}
                          borderRadius="md"
                          px={3}
                          py={2}
                          size="sm"
                          sx={{ ".chakra-radio__control": { w: 3, h: 3 } }}
                        >
                          <HStack spacing={2} flexWrap="wrap" rowGap={1}>
                            <Badge variant="subtle" colorScheme="purple">#{b.id}</Badge>
                            <Badge variant="outline">{(b.tipo_turno || "").toUpperCase()}</Badge>
                            {Number.isFinite(Number(b.valor)) && (
                              <Badge variant="solid" colorScheme="green">
                                − ${Number(b.valor).toLocaleString("es-AR")}
                              </Badge>
                            )}
                            {vence && (
                              <Badge variant="outline" colorScheme="orange">vence {vence}</Badge>
                            )}
                            {b.motivo && (
                              <Text fontSize="sm" color={muted} wordBreak="break-word">— {b.motivo}</Text>
                            )}
                          </HStack>
                        </Box>
                      );
                    })}
                  </Stack>
                </Box>
              </RadioGroup>
            </Box>
          )}

          {/* Valor restante (elegante, arriba del footer) */}
          <Box
            mt={{ base: 3, md: 4 }}
            mb={{ base: 2, md: 3 }}
            p={{ base: 3, md: 4 }}
            borderRadius="xl"
            bg={useColorModeValue("blackAlpha.50", "whiteAlpha.100")}
            border="2px solid"
            borderColor={resumenBorder}
            textAlign="center"
          >
            <Text fontSize={{ base: "sm", md: "md" }} color={muted}>Valor restante</Text>
            <Text fontSize={{ base: "3xl", md: "4xl" }} fontWeight="extrabold" lineHeight="1.1">
              ${Number(valorRestante).toLocaleString("es-AR")}
            </Text>
            {selectedBono && (
              <Text fontSize={{ base: "xs", md: "sm" }} mt={1} color={muted}>
                {`$${Number(precioClase).toLocaleString("es-AR")} − $${Number(valorBono).toLocaleString("es-AR")} = $${Number(valorRestante).toLocaleString("es-AR")}`}
              </Text>
            )}
          </Box>

          {/* Dropzone (solo si resta > 0) */}
          {needsComprobante && (
            <>
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
                mt={{ base: 2, md: 2 }}
                mb={{ base: 2, md: 3 }}
              >
                <Input
                  id="archivo"
                  type="file"
                  display="none"
                  onChange={(e) => onArchivoChange(e.target.files[0])}
                />
                <Text color="gray.500" fontSize={{ base: "xs", md: "sm" }} fontWeight="medium" wordBreak="break-word">
                  {archivo ? `📄 ${archivo.name}` : "📎 Subí el comprobante de pago"}
                </Text>
              </Box>

              {archivo && (
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

              {/* Aviso contextual — solo cuando hace falta y falta el archivo */}
              {!archivo && (
                <Alert status="warning" borderRadius="lg" mt={1}>
                  <AlertIcon />
                  Falta comprobante. Subí el comprobante para confirmar.
                </Alert>
              )}
            </>
          )}

          <Divider my={{ base: 2, md: 3 }} opacity={0.35} />

          <Text fontSize={{ base: "xs", md: "sm" }} color="gray.500" mt={{ base: 1, md: 2 }} wordBreak="break-word">
            <b>📋 Política de reserva:</b> La bonificación se valida en backend. Si el valor restante es mayor a $0, necesitás comprobante.
            Las cancelaciones sólo se permiten con <b>mínimo 24 h de anticipación</b>. Si no confirmás antes del fin del contador, el turno se libera.
          </Text>
        </ModalBody>

        <ModalFooter flexWrap={{ base: "wrap", md: "nowrap" }} gap={{ base: 2, md: 3 }}>
          <Button
            colorScheme="blue"
            mr={{ base: 0, md: 3 }}
            isLoading={loading}
            onClick={() => onConfirmar(selectedBonoId)}
            size={{ base: "sm", md: "md" }}
            flexShrink={0}
            isDisabled={confirmDisabled}
          >
            Confirmar reserva
          </Button>
          <Button variant="ghost" onClick={onClose} size={{ base: "sm", md: "md" }} flexShrink={0}>
            Cancelar
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default ReservaPagoModal;
