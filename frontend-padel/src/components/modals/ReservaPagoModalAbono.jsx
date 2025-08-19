// src/components/modals/ReservaPagoModalAbono.jsx
import React, { useMemo } from "react";
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

const LABELS = { x1: "Individual", x2: "2 Personas", x3: "3 Personas", x4: "4 Personas" };

const ReservaPagoModalAbono = ({
  alias,
  cbuCvu,
  isOpen,
  onClose,
  turno,                 // {fecha, hora}
  tipoClase,             // {id, codigo, nombre?, precio}
  precioAbono = 0,       // 💰 precio mensual del abono (viene de /padel/tipos-abono)
  precioUnitario = 0,    // 💸 descuento por cada bonificación (usamos tipo_clase.precio)
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
  const segundos = Number(tiempoRestante ?? 180);
  const nombreTipo = (tipoClase?.nombre) || LABELS[tipoClase?.codigo] || "—";

  const bonosOrdenados = useMemo(() => {
    // Ordenar por vencimiento ascendente (nulos al final)
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

  // 🪵 logs
  console.debug("[ModalAbono] render", {
    tipoClase,
    precioAbono,
    precioUnitario,
    bonosDisponibles: bonificaciones?.length || 0,
    selectedBonos,
    totalEstimado,
    hideComprobante,
  });

  const toggleAll = (checkAll) => {
    if (checkAll) {
      setSelectedBonos((bonosOrdenados || []).map((b) => b.id));
    } else {
      setSelectedBonos([]);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} isCentered size="lg" motionPreset="slideInBottom">
      <ModalOverlay />
      <ModalContent bg={modalBg} color={modalText} px={6} py={4} borderRadius="2xl">
        <ModalHeader fontWeight="bold" fontSize="lg" color="blue.300">
          Confirmar pago de abono
        </ModalHeader>
        <ModalCloseButton />

        <ModalBody>
          {(turno?.fecha || turno?.hora) && (
            <Box
              mb={5}
              border="2px solid"
              borderColor={resumenBorder}
              bg={resumenBg}
              color={resumenText}
              borderRadius="md"
              px={4}
              py={3}
            >
              {turno.fecha && (
                <Flex align="center" gap={3}>
                  <Icon as={FaCalendarAlt} boxSize={5} />
                  <Text>
                    <b>Mes/Día:</b> {turno.fecha}
                  </Text>
                </Flex>
              )}
              {turno.hora && (
                <Flex align="center" gap={3} mt={2}>
                  <Icon as={FaClock} boxSize={5} />
                  <Text>
                    <b>Hora:</b> {(turno.hora || "").slice(0, 5)} hs
                  </Text>
                </Flex>
              )}
            </Box>
          )}

          {tipoClase && (
            <Box mb={4}>
              <Text>
                <b>Tipo de clase:</b> {nombreTipo}
              </Text>
              <Text>
                <b>Precio del abono:</b>{" "}
                ${Number(precioAbono).toLocaleString("es-AR")}
              </Text>
              <Text>
                <b>Descuento por bonificación:</b>{" "}
                ${Number(precioUnitario).toLocaleString("es-AR")} c/u
              </Text>
              {alias && (
                <Text>
                  <b>Alias:</b> {alias}
                </Text>
              )}
              {cbuCvu && (
                <Text>
                  <b>CBU/CVU:</b> {cbuCvu}
                </Text>
              )}
            </Box>
          )}

          {/* Countdown (fallback si el componente no está disponible) */}
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
              <Text fontSize="sm" color="orange.500">
                Contador no disponible (ver consola). No afecta a la confirmación.
              </Text>
            </Box>
          )}

          {/* Resumen del cálculo */}
          <Box
            mt={4}
            mb={3}
            p={3}
            borderRadius="md"
            border="1px solid"
            borderColor={resumenBorder}
            bg={`${resumenBg}66`}
          >
            <Text fontSize="sm">
              Total estimado:{" "}
              <b>${Number(totalEstimado).toLocaleString("es-AR")}</b>{" "}
              = ${Number(precioAbono).toLocaleString("es-AR")} − (
              {selectedBonos.length} × $
              {Number(precioUnitario).toLocaleString("es-AR")})
            </Text>
          </Box>

          {/* Bonificaciones: selección amigable */}
          {!!bonosOrdenados.length && (
            <Box
              mt={4}
              mb={4}
              p={4}
              borderRadius="md"
              bg={`${resumenBg}88`}
              border="1px solid"
              borderColor={resumenBorder}
            >
              <HStack justify="space-between" align="center" mb={2}>
                <Text fontWeight="medium">
                  Tenés {bonosOrdenados.length} bonificación
                  {bonosOrdenados.length > 1 ? "es" : ""} disponibles. Elegí
                  cuáles aplicar al <b>mes actual</b>:
                </Text>
                <HStack>
                  <Button
                    size="xs"
                    variant="outline"
                    onClick={() => toggleAll(true)}
                  >
                    Seleccionar todas
                  </Button>
                  <Button
                    size="xs"
                    variant="ghost"
                    onClick={() => toggleAll(false)}
                  >
                    Ninguna
                  </Button>
                </HStack>
              </HStack>

              <Stack spacing={2}>
                {bonosOrdenados.map((b) => {
                  const checked = selectedBonos.includes(b.id);
                  const vence =
                    b.valido_hasta &&
                    new Date(b.valido_hasta).toLocaleDateString("es-AR");
                  const tipo =
                    (b.tipo_turno || "").toUpperCase(); // ej: x1
                  return (
                    <Checkbox
                      key={b.id}
                      isChecked={checked}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedBonos([...selectedBonos, b.id]);
                        } else {
                          setSelectedBonos(
                            selectedBonos.filter((x) => x !== b.id)
                          );
                        }
                      }}
                      colorScheme="teal"
                    >
                      <HStack spacing={2}>
                        <Badge variant="subtle" colorScheme="purple">
                          #{b.id}
                        </Badge>
                        <Badge variant="outline">{tipo}</Badge>
                        {vence && (
                          <Badge variant="outline" colorScheme="orange">
                            vence {vence}
                          </Badge>
                        )}
                        {b.motivo && (
                          <Text fontSize="sm" color="gray.500">
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
              px={4}
              py={4}
              minH="60px"
              rounded="lg"
              w="100%"
              cursor="pointer"
              display="flex"
              alignItems="center"
              justifyContent="center"
              textAlign="center"
              _hover={{ borderColor: "green.400", bg: dropzoneHover }}
              mt={2}
              mb={3}
            >
              <Input
                id="archivo"
                type="file"
                display="none"
                onChange={(e) => onArchivoChange(e.target.files[0])}
              />
              <Text color="gray.500" fontSize="sm" fontWeight="medium">
                {archivo
                  ? `📄 ${archivo.name}`
                  : "📎 Subí el comprobante de pago del abono"}
              </Text>
            </Box>
          )}

          {archivo && !hideComprobante && (
            <Button
              size="sm"
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
              mt={2}
              mb={3}
              p={3}
              borderRadius="md"
              border="1px dashed"
              borderColor={resumenBorder}
              bg={`${resumenBg}66`}
            >
              <Text fontSize="sm" color="gray.700">
                Con <b>{selectedBonos.length}</b> bonificación
                {selectedBonos.length > 1 ? "es" : ""} el total es{" "}
                <b>$0</b>. Comprobante <b>no requerido</b>.
              </Text>
            </Box>
          )}

          <Text fontSize="sm" color="gray.500" mt={4}>
            <b>📋 Política de abono:</b> Reservamos todas las fechas del mes
            actual y prioridad del próximo. El total se recalcula en backend y
            podría ajustar según reglas internas.
          </Text>
        </ModalBody>

        <ModalFooter>
          <Button
            colorScheme="blue"
            mr={3}
            isLoading={loading}
            onClick={() => onConfirmar(selectedBonos)}
          >
            Confirmar pago de abono
          </Button>
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default ReservaPagoModalAbono;
