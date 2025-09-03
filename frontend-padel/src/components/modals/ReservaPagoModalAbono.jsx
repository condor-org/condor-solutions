// src/components/modals/ReservaPagoModalAbono.jsx
import React, { useMemo, useRef } from "react";
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
  Checkbox,
  Stack,
  HStack,
} from "@chakra-ui/react";
import { FaCalendarAlt, FaClock, FaTrash } from "react-icons/fa";
import CountdownClock from "../ui/CountdownClock";
import { CopyIcon } from "@chakra-ui/icons";
import { useToast, Tooltip, IconButton } from "@chakra-ui/react";
const LABELS = { x1: "Individual", x2: "2 Personas", x3: "3 Personas", x4: "4 Personas" };





const ReservaPagoModalAbono = ({
  alias,
  cbuCvu,
  isOpen,
  onClose,
  turno,                 // {fecha, hora}
  tipoClase,             // {id, codigo, nombre?, precio}
  precioAbono = 0,       // 💰 precio mensual del abono
  precioUnitario = 0,    // 💸 descuento por cada bonificación (tipo_clase.precio)
  archivo,
  onArchivoChange,
  onRemoveArchivo,
  onConfirmar,           // (selectedBonosIds[]) => void
  loading,
  tiempoRestante,
  bonificaciones = [],   // [{id, motivo, tipo_turno, fecha_creacion, valido_hasta}]
  selectedBonos = [],
  setSelectedBonos,
}) => {
  // 🎨 tokens
  const modalBg = useColorModeValue("white", "gray.900");
  const modalText = useColorModeValue("gray.800", "white");
  const resumenBg = useColorModeValue("green.50", "green.900");
  const resumenBorder = useColorModeValue("green.400", "green.500");
  const resumenText = useColorModeValue("green.800", "green.200");
  const dropzoneBg = useColorModeValue("gray.100", "#232b34");
  const dropzoneHover = useColorModeValue("gray.200", "#243039");
  const dropzoneBorder = useColorModeValue("green.500", "#27ae60");

  // 🧮 cálculos
  const segundos = Number(tiempoRestante ?? 900);
  const nombreTipo = (tipoClase?.nombre) || LABELS[tipoClase?.codigo] || "—";

  const bonosOrdenados = useMemo(() => {
    const clone = Array.isArray(bonificaciones) ? [...bonificaciones] : [];
    return clone.sort((a, b) => {
      const va = a?.valido_hasta ? new Date(a.valido_hasta).getTime() : Infinity;
      const vb = b?.valido_hasta ? new Date(b.valido_hasta).getTime() : Infinity;
      return va - vb;
    });
  }, [bonificaciones]);

  const totalEstimado = useMemo(() => {
    const bonosN = Number(selectedBonos?.length || 0);
    const total = Math.max(0, Number(precioAbono) - bonosN * Number(precioUnitario));
    return total;
  }, [precioAbono, precioUnitario, selectedBonos]);

  const hideComprobante = totalEstimado <= 0;

  const toggleAll = (checkAll) => {
    if (checkAll) setSelectedBonos((bonosOrdenados || []).map((b) => b.id));
    else setSelectedBonos([]);
  };

  const toast = useToast();
  const hiddenInputRef = useRef(null);

  const copyText = async (text, label = "Texto") => {
    try {
      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
      } else {
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
      console.debug(`[ReservaPagoModalAbono] Copiado a portapapeles: ${label}`);
    } catch (err) {
      console.error(`[ReservaPagoModalAbono] Error al copiar ${label}:`, err);
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
          Confirmar pago de abono
        </ModalHeader>
        <ModalCloseButton />

        <ModalBody>
          {(turno?.fecha || turno?.hora) && (
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
              {turno.fecha && (
                <Flex align="center" gap={{ base: 2, md: 3 }} wrap="wrap">
                  <Icon as={FaCalendarAlt} boxSize={{ base: 4, md: 5 }} />
                  <Text fontSize={{ base: "sm", md: "md" }} whiteSpace="normal">
                    <b>Mes/Día:</b> {turno.fecha}
                  </Text>
                </Flex>
              )}
              {turno.hora && (
                <Flex align="center" gap={{ base: 2, md: 3 }} mt={2} wrap="wrap">
                  <Icon as={FaClock} boxSize={{ base: 4, md: 5 }} />
                  <Text fontSize={{ base: "sm", md: "md" }} whiteSpace="normal">
                    <b>Hora:</b> {(turno.hora || "").slice(0, 5)} hs
                  </Text>
                </Flex>
              )}
            </Box>
          )}

          {tipoClase && (
            <Box mb={{ base: 3, md: 4 }} wordBreak="break-word">
              <Text fontSize={{ base: "sm", md: "md" }}>
                <b>Tipo de clase:</b> {nombreTipo}
              </Text>
              <Text fontSize={{ base: "sm", md: "md" }}>
                <b>Precio del abono:</b> ${Number(precioAbono).toLocaleString("es-AR")}
              </Text>
              <Text fontSize={{ base: "sm", md: "md" }}>
                <b>Descuento por bonificación:</b> ${Number(precioUnitario).toLocaleString("es-AR")} c/u
              </Text>

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


          {/* Countdown */}
          {CountdownClock ? (
            <CountdownClock
              segundosTotales={segundos}
              size="md"
              showLabel={true}
              colorScheme="green"
              onFinalizar={() => {
                onClose();
                alert("⏱ El tiempo para confirmar la operación ha finalizado.");
              }}
            />
          ) : (
            <Box
              mt={2}
              mb={2}
              p={3}
              borderRadius="md"
              border="1px dashed"
              borderColor={resumenBorder}
              bg={`${resumenBg}66`}
            >
              <Text fontSize={{ base: "xs", md: "sm" }} color="orange.500">
                Contador no disponible (ver consola). No afecta a la confirmación.
              </Text>
            </Box>
          )}

          {/* Resumen del cálculo (solo si hay bonos y el usuario activó alguno) */}
          {bonosOrdenados.length > 0 && selectedBonos.length > 0 && (
            <Box
              mt={{ base: 3, md: 4 }}
              mb={{ base: 2, md: 3 }}
              p={3}
              borderRadius="md"
              border="1px solid"
              borderColor={resumenBorder}
              bg={`${resumenBg}66`}
              wordBreak="break-word"
            >
              <Text fontSize={{ base: "sm", md: "sm" }}>
                Total estimado:{" "}
                <b>${Number(totalEstimado).toLocaleString("es-AR")}</b>{" "}
                = ${Number(precioAbono).toLocaleString("es-AR")} − (
                {selectedBonos.length} × $
                {Number(precioUnitario).toLocaleString("es-AR")})
              </Text>
            </Box>
          )}


          {/* Bonificaciones */}
          {!!bonosOrdenados.length && (
            <Box
              mt={{ base: 3, md: 4 }}
              mb={{ base: 3, md: 4 }}
              p={{ base: 3, md: 4 }}
              borderRadius="md"
              bg={`${resumenBg}88`}
              border="1px solid"
              borderColor={resumenBorder}
            >
              <HStack justify="space-between" align="center" mb={2} flexWrap="wrap" rowGap={2}>
                <Text fontWeight="medium" fontSize={{ base: "sm", md: "md" }}>
                  Tenés {bonosOrdenados.length} bonificación
                  {bonosOrdenados.length > 1 ? "es" : ""} disponibles. Elegí
                  cuáles aplicar al <b>mes actual</b>:
                </Text>
                <HStack>
                  <Button size="xs" variant="outline" onClick={() => toggleAll(true)}>
                    Seleccionar todas
                  </Button>
                  <Button size="xs" variant="ghost" onClick={() => toggleAll(false)}>
                    Ninguna
                  </Button>
                </HStack>
              </HStack>

              {/* En móvil, lista scrolleable si es larga */}
              <Stack
                spacing={2}
                maxH={{ base: '35vh', md: 'none' }}
                overflowY={{ base: 'auto', md: 'visible' }}
                pr={{ base: 1, md: 0 }}
              >
                {bonosOrdenados.map((b) => {
                  const checked = selectedBonos.includes(b.id);
                  const vence = b.valido_hasta && new Date(b.valido_hasta).toLocaleDateString("es-AR");
                  const tipo = (b.tipo_turno || "").toUpperCase(); // ej: x1
                  return (
                    <Checkbox
                      key={b.id}
                      isChecked={checked}
                      onChange={(e) => {
                        if (e.target.checked) setSelectedBonos([...selectedBonos, b.id]);
                        else setSelectedBonos(selectedBonos.filter((x) => x !== b.id));
                      }}
                      colorScheme="teal"
                    >
                      <HStack spacing={2} flexWrap="wrap" rowGap={1}>
                        <Badge variant="subtle" colorScheme="purple">#{b.id}</Badge>
                        <Badge variant="outline">{tipo}</Badge>
                        {vence && (
                          <Badge variant="outline" colorScheme="orange">
                            vence {vence}
                          </Badge>
                        )}
                        {b.motivo && (
                          <Text fontSize="sm" color="gray.500" wordBreak="break-word">
                            — {b.motivo}
                          </Text>
                        )}
                      </HStack>
                    </Checkbox>
                  );
                })}
              </Stack>

              <Badge mt={3} colorScheme={selectedBonos.length ? "purple" : "gray"}>
                Seleccionadas: {selectedBonos.length}
              </Badge>
            </Box>
          )}

          {/* Dropzone de comprobante (se oculta si el total es 0) */}
          {!hideComprobante && (
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
                {archivo ? `📄 ${archivo.name}` : "📎 Subí el comprobante de pago del abono"}
              </Text>
            </Box>
          )}

          {archivo && !hideComprobante && (
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

          {hideComprobante && (
            <Box
              mt={{ base: 2, md: 2 }}
              mb={{ base: 2, md: 3 }}
              p={3}
              borderRadius="md"
              border="1px dashed"
              borderColor={resumenBorder}
              bg={`${resumenBg}66`}
              wordBreak="break-word"
            >
              <Text fontSize={{ base: "xs", md: "sm" }} color="gray.700">
                Con <b>{selectedBonos.length}</b> bonificación
                {selectedBonos.length > 1 ? "es" : ""} el total es <b>$0</b>. Comprobante <b>no requerido</b>.
              </Text>
            </Box>
          )}

          <Text fontSize={{ base: "xs", md: "sm" }} color="gray.500" mt={{ base: 2, md: 4 }} wordBreak="break-word">
            <b>📋 Política de abono:</b> Reservamos todas las fechas del mes actual y prioridad del próximo.
            El total se recalcula en backend y podría ajustar según reglas internas.
          </Text>
        </ModalBody>

        <ModalFooter flexWrap={{ base: "wrap", md: "nowrap" }} gap={{ base: 2, md: 3 }}>
          <Button
            colorScheme="blue"
            mr={{ base: 0, md: 3 }}
            isLoading={loading}
            onClick={() => onConfirmar(selectedBonos)}
            size={{ base: "sm", md: "md" }}
            flexShrink={0}
          >
            Confirmar pago de abono
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

export default ReservaPagoModalAbono;
